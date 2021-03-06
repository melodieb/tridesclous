import numpy as np
import os
import time

import sklearn
import sklearn.cluster
import sklearn.mixture
import sklearn.metrics

import scipy.signal
import scipy.stats
from sklearn.neighbors import KernelDensity

from . import labelcodes
from .tools import median_mad


import matplotlib.pyplot as plt


def find_clusters(catalogueconstructor, method='kmeans', selection=None, **kargs):
    cc = catalogueconstructor
    
    if selection is None:
        features = cc.some_features
        waveforms = cc.some_waveforms
    else:
        sel = selection[cc.some_peaks_index]
        features = cc.some_features[sel]
        waveforms = cc.some_waveforms[sel]
    
    if waveforms.shape[0] == 0:
        print('oupas waveforms vide')
        return
    
    if method == 'kmeans':
        km = sklearn.cluster.KMeans(n_clusters=kargs.pop('n_clusters'),**kargs)
        labels = km.fit_predict(features)
    elif method == 'onecluster':
        labels = np.zeros(features.shape[0], dtype='int64')
    elif method == 'gmm':
        gmm = sklearn.mixture.GaussianMixture(n_components=kargs.pop('n_clusters'),**kargs)
        #~ labels =gmm.fit_predict(features)
        gmm.fit(features)
        labels =gmm.predict(features)
    #~ elif method == 'kmedois':
        #~ import pyclust
        #~ km = pyclust.KMedoids(n_clusters=kargs.pop('n_clusters'))
        #~ labels = km.fit_predict(features)
    elif method == 'agglomerative':
        agg = sklearn.cluster.AgglomerativeClustering(n_clusters=kargs.pop('n_clusters'), **kargs)
        labels = agg.fit_predict(features)
    elif method == 'dbscan':
        dbscan = sklearn.cluster.DBSCAN(**kargs)
        labels = dbscan.fit_predict(features)
    elif method == 'sawchaincut':
        n_left = cc.info['params_waveformextractor']['n_left']
        n_right = cc.info['params_waveformextractor']['n_right']
        peak_sign = cc.info['params_peakdetector']['peak_sign']
        relative_threshold = cc.info['params_peakdetector']['relative_threshold']
        #~ sawchaincut = SawChainCut_OLD(waveforms, n_left, n_right, peak_sign, relative_threshold)
        sawchaincut = SawChainCut(waveforms, n_left, n_right, peak_sign, relative_threshold)
        labels = sawchaincut.do_the_job()
        #~ print('ici trash nb', np.sum(labels==-1))
    else:
        raise(ValueError, 'find_clusters method unknown')
    
    if selection is None:
        #~ cc.all_peaks['cluster_label'][:] = labelcodes.LABEL_NO_WAVEFORM
        cc.all_peaks['cluster_label'][cc.some_peaks_index] = labels
    else:
        labels[labels>=0] += max(max(cc.cluster_labels), -1) + 1
        cc.all_peaks['cluster_label'][cc.some_peaks_index[sel]] = labels
    
    
    return labels




class SawChainCut:
    def __init__(self, waveforms, n_left, n_right, peak_sign, threshold):
        self.waveforms = waveforms
        self.n_left = n_left
        self.n_right = n_right
        self.width = n_right - n_left
        self.peak_sign = peak_sign
        
        self.threshold = threshold
        
        self.binsize = 0.1
        self.kde_bandwith  = 0.4
        self.minima_rejection_factor = .3
        self.nb_min = 20
        self.threshold_margin = 1.
        self.margin_first_max = 1.
        
        self.max_loop = 1000
        self.break_nb_remain = 30


    def do_the_job(self):
        
        cluster_labels = self.split_loop()
        #~ cluster_labels = self.merge_loop(cluster_labels)
        
        return cluster_labels
    
    def one_cut(self, x):

        #~ x = x[x>(thresh-threshold_margin)]
        #~ kde = scipy.stats.gaussian_kde(x, bw_method=kde_bandwith)
        #~ d = kde(bins)
        #~ d /= np.sum(d)
        
        kde = KernelDensity(kernel='gaussian', bandwidth=self.kde_bandwith)
        d = kde.fit(x[:, np.newaxis]).score_samples(self.bins[:, np.newaxis])
        d = np.exp(d)



        #local max
        d0, d1, d2 = d[:-2], d[1:-1], d[2:]
        #~ ind_max,  = np.nonzero((d0<d1) & (d2<d1))
        ind_max,  = np.nonzero((d0<d1) & (d2<=d1))
        ind_max += 1
        #~ ind_min,  = np.nonzero((d0>d1) & (d2>d1))
        ind_min,  = np.nonzero((d0>d1) & (d2>=d1))
        ind_min += 1
        
        #~ print('ind_max', ind_max)
        #~ print('ind_min', ind_min)
        #~ fig, ax = plt.subplots()
        #~ ax.plot(d)
        #~ ax.plot(ind_max, d[ind_max], ls='None', marker='o', color='r')
        #~ ax.plot(ind_min, d[ind_min], ls='None', marker='o', color='g')
        #~ plt.show()

        if ind_max.size>0:
            if ind_min.size==0:
                assert ind_max.size==1, 'Super louche pas de min mais plusieur max'
                ind_min = np.array([0, self.bins.size-1], dtype='int64')
            else:
                ind_min = ind_min.tolist()
                if ind_max[0]<ind_min[0]:
                    ind_min = [0] + ind_min
                if ind_max[-1]>ind_min[-1]:
                    ind_min = ind_min + [ self.bins.size-1]
                ind_min = np.array(ind_min, dtype='int64')
        
        
        #Loop reject small rebounce minimam/maxima
        #~ print('loop1')
        ind_max_cleaned = ind_max.tolist()
        ind_min_cleaned = ind_min.tolist()
        while True:
            rejected_minima = None
            rejected_maxima = None
            #~ print('ind_min_cleaned', ind_min_cleaned, self.bins[ind_min_cleaned])
            #~ print('ind_max_cleaned', ind_max_cleaned, self.bins[ind_max_cleaned])
            for i, ind in enumerate(ind_min_cleaned[1:-1]):
                prev_max = ind_max_cleaned[i]
                next_max = ind_max_cleaned[i+1]
                
                delta_density_prev = d[prev_max] - d[ind]
                delta_density_next = d[next_max] - d[ind]
                
                if min(delta_density_prev, delta_density_next)<d[ind]*self.minima_rejection_factor:
                    rejected_minima = ind
                    if delta_density_prev<delta_density_next:
                        rejected_maxima = prev_max
                    else:
                        rejected_maxima = next_max
                    break
            
            if rejected_minima is None:
                break
            
            ind_max_cleaned.remove(rejected_maxima)
            ind_min_cleaned.remove(rejected_minima)
        
        #~ print('loop2')
        #loop reject density with too few spikes
        while True:
            rejected_minima = None
            rejected_maxima = None
            
            #~ print('ind_min_cleaned', ind_min_cleaned, self.bins[ind_min_cleaned])
            #~ print('ind_max_cleaned', ind_max_cleaned, self.bins[ind_max_cleaned])
            
            for i, ind in enumerate(ind_min_cleaned[:-1]):
                next_min = ind_min_cleaned[i+1]
                n = np.sum(d[ind:next_min]*self.binsize) * x.size
                #~ print('n', n, self.bins[ind], self.bins[next_min], np.sum(d))
                if n<self.nb_min:
                    rejected_maxima = ind_max_cleaned[i]
                    if d[ind]<d[next_min]:
                        rejected_minima = next_min
                    else:
                        rejected_minima = ind
                    break
            
            if rejected_minima is None:
                break
            
            ind_max_cleaned.remove(rejected_maxima)
            ind_min_cleaned.remove(rejected_minima)
            

        #~ print('loop3')
        #TODO eliminate first avec meme critere loop 1
        if len(ind_min_cleaned)>=2:
            den_min0 = d[ind_min_cleaned[0]]
            den_max0 = d[ind_max_cleaned[0]]
            if (den_max0-den_min0)<den_min0*self.minima_rejection_factor:
                ind_min_cleaned = ind_min_cleaned[1:]
                ind_max_cleaned = ind_max_cleaned[1:]
        
        #~ print('loop4')
        if len(ind_min_cleaned)>=2:
            if self.bins[ind_max_cleaned[0]]<self.threshold+self.margin_first_max:
                ind_min_cleaned = ind_min_cleaned[1:]
                ind_max_cleaned = ind_max_cleaned[1:]
        
        
        if len(ind_min_cleaned)>=2:
            #TODO here criterium for best
            return self.bins[ind_min_cleaned[-2]], self.bins[ind_min_cleaned[-1]], d
        else:
            return None, None, d
        
    
    def split_loop(self):
        ind_peak = -self.n_left
        all_peak_max = self.waveforms[:, ind_peak, : ].copy()
        if self.peak_sign == '-' :
            all_peak_max = -all_peak_max
        
        nb_channel = self.waveforms.shape[2]
        self.bins = np.arange(self.threshold, np.max(all_peak_max),  self.binsize)
        
        cluster_labels = np.zeros(self.waveforms.shape[0], dtype='int64')
        k = 0
        chan_visited = []
        #~ for iloop in range(self.max_loop):
        iloop = -1
        while True:
            iloop += 1
            
            nb_remain = np.sum(cluster_labels>=k)
            sel = cluster_labels == k
            nb_working = np.sum(sel)
            print()
            print('iloop', iloop, 'k', k, 'nb_remain', nb_remain, 'nb_working', nb_working, {True:'full', False:'partial'}[nb_remain==nb_working])
            
            if iloop>=self.max_loop:
                cluster_labels[sel] = -1
                print('BREAK iloop', iloop)
                break
            
            if iloop!=0 and nb_remain<self.break_nb_remain:
                cluster_labels[sel] = -1
                print('BREAK nb_remain', nb_remain, '<', self.break_nb_remain)
                break
            
            #~ print(all_peak_max.shape)
            peak_max = all_peak_max[sel, :]
            
            
            if nb_working<self.nb_min:
                print('TRASH: too few')
                cluster_labels[sel] = -1
                k += 1
                chan_visited = []
                continue
            
            percentiles = np.zeros(nb_channel)
            for c in range(nb_channel):
                x = peak_max[:, c]
                x = x[x>self.threshold]
                
                if x.size>self.nb_min:
                    per = np.nanpercentile(x, 90)
                else:
                    per = 0
                percentiles[c] = per
            order_visit = np.argsort(percentiles)[::-1]
            order_visit = order_visit[percentiles[order_visit]>0]
            
            #~ print(order_visit)
            #~ print(percentiles[order_visit])
            
            
            order_visit = order_visit[~np.in1d(order_visit, chan_visited)]
            
            if len(order_visit)==0:
                print('len(order_visit)==0')
                if np.sum(cluster_labels>k)>0:
                    k+=1
                    chan_visited = []
                    continue
                else:
                    cluster_labels[sel] = -1
                    print('BREAK no  more channel')
                    break
            
            actual_chan = order_visit[0]
            x = peak_max[:, actual_chan]
            x = x[x>(self.threshold-self.threshold_margin)]
            lim0, lim1, density_ = self.one_cut(x)
            #~ print('lim0, lim1', lim0, lim1)
            
            #~ if True:
            if False:
                if not os.path.exists('debug_sawchaincut'):
                    os.mkdir('debug_sawchaincut')
                
                if hasattr(self, 'n_cut'):
                    self.n_cut += 1
                else:
                    self.n_cut = 0
                    #~ fig, ax = plt.subplots()
                    #~ ax.plot(np.arange(self.smooth_kernel.size)*self.binsize, self.smooth_kernel)
                    #~ fig.savefig('debug_sawchaincut/smooth_kernel.png')
                
                count, _ = np.histogram(x, bins=self.bins)
                count = count.astype(float)/np.sum(count)
                
                filename = 'debug_sawchaincut/one_cut {}.png'.format(self.n_cut)
                fig, ax = plt.subplots()
                
                ax.set_title('nb_remain {}, nb_working {},  chan {} , x.size {}, k {} {}'.format(nb_remain, nb_working, actual_chan, x.size, k, {True:'full', False:'partial'}[nb_remain==nb_working]))
                ax.plot(self.bins[:-1], count, color='b')
                ax.plot(self.bins, density_, color='k')
                
                ax.set_xlim(0, self.bins[-1]+.5)
                ax.set_ylim(0,max(density_)*1.2)
                
                if lim0 is not None:
                    ax.axvline(lim0, color='k')
                    ax.axvline(lim1, color='k')
                
                fig.savefig(filename)
                
                #~ plt.show()
            
            #~ print(feat[labels==0].size, feat[labels==1].size)
            
            
            if lim0 is None:
                chan_visited.append(actual_chan)
                print('EXPLORE NEW DIM lim0 is None ',  len(chan_visited))
                continue
            
            
            ind, = np.nonzero(sel)
            #~ print(ind.shape)
            not_in = ~((peak_max[:, actual_chan]>lim0) & (peak_max[:, actual_chan]<lim1))
            #~ print(not_in.shape)
            cluster_labels[cluster_labels>k] += 1#TODO reflechir la dessus!!!
            cluster_labels[ind[not_in]] += 1

            if np.sum(not_in)==0:
                print('ACCEPT: not_in.sum()==0')
                k+=1
                chan_visited = []
                continue
        
        print('END loop', np.sum(cluster_labels==-1))
        return cluster_labels





class SawChainCut_OLD:
    def __init__(self, waveforms, n_left, n_right, peak_sign, threshold):
        self.waveforms = waveforms
        self.n_left = n_left
        self.n_right = n_right
        self.width = n_right - n_left
        self.peak_sign = peak_sign
        
        self.threshold = threshold
        
        self.binsize = 0.1
        self.kde_bandwith  = 0.2
        
        self.nb_min = 10
        
        self.max_loop = 1000
        
        self.break_nb_remain = 30
        
        self.threshold_similarity = 0.9
        
        self.debug = True
        #~ self.debug = False
        
        

    
    
    def one_cut(self, x):
        labels = np.zeros(x.size, dtype='int64')
        
        # test with histogram
        #~ count, bins = np.histogram(x, bins=self.bins)
        #~ density = np.convolve(count, self.smooth_kernel, mode='same')
        #~ bins = bins[:1]
        
        # test with kernel density
        #~ kernel = stats.gaussian_kde(values)
        
        #TODO: adapt self.kde_bandwith with N
        kde = scipy.stats.gaussian_kde(x, bw_method=self.kde_bandwith)
        #~ print('kde.factor', kde.factor)
        density = kde(self.bins)
        density /= np.sum(density)
        #~ print('density', np.sum(density))

        bins = self.bins.copy()
        #TODO work on this
        keep_bins = np.abs(bins)>self.threshold
        #~ keep_bins = np.abs(bins)>3.5
        bins = bins[keep_bins]
        density = density[keep_bins]
        
        
        
        #~ density[np.abs(bins)<self.threshold] = 0
        #~ density[np.abs(bins)<3.5] = 0
        

        # maxima
        local_max_indexes, = np.nonzero((density[1:-1]>density[:-2])& (density[1:-1]>=density[2:]))
        #~ keep = np.abs(bins[local_max_indexes])>(self.threshold + self.binsize)
        #~ local_max_indexes = local_max_indexes[keep]
        local_max_indexes += 1
        
        # minima
        local_min_indexes, = np.nonzero((density[1:-1]<density[:-2])& (density[1:-1]<=density[2:]))
        #~ keep = np.abs(bins[local_min_indexes])>(self.threshold + self.binsize)
        #~ local_min_indexes = local_min_indexes[keep]
        local_min_indexes += 1
        if density[-1]<=density[-2]:
            #special case lest border
            local_min_indexes = np.concatenate([local_min_indexes, [bins.size-1]])
        
        #~ import matplotlib.pyplot as plt
        #~ fig, ax = plt.subplots()
        #~ ax.plot(bins, density)
        #~ ax.plot(bins[local_max_indexes], density[local_max_indexes], ls='None',marker='o')
        #~ ax.plot(bins[local_min_indexes], density[local_min_indexes], ls='None',marker='o')
        #~ plt.show()
        
        #keep a local minimum in density if near max are big
        #~ print('local_max_indexes', local_max_indexes, bins[local_max_indexes])
        #~ print('local_min_indexes', local_min_indexes, bins[local_min_indexes])
        for i, ind in enumerate(local_min_indexes):
            lim = bins[ind]
            #~ print('ici', ind, lim, np.sum(x<=lim))
            #TODO trash too small 
            if self.peak_sign == '-' and np.sum(x<=lim)<=self.nb_min:
                local_min_indexes[i] = -1
                #~ print('REJECT under self.nb_min')
            elif self.peak_sign == '+' and np.sum(x>=lim)<=self.nb_min:
                local_min_indexes[i] = -1
                #~ print('REJECT under self.nb_min')
            
            i_r = np.searchsorted(local_max_indexes, ind, side='left')
            i_l = i_r - 1
            if i_r>=len(local_max_indexes):
                break
            delta_l = density[local_max_indexes[i_l]] - density[ind]
            delta_r = density[local_max_indexes[i_r]] - density[ind]
            #~ print('search', ind, i_l, local_max_indexes[i_l], i_r, local_max_indexes[i_r])
            #~ print('delta_l', delta_l, 'delta_r', delta_r, 'density[ind]', density[ind])
            
            if min(delta_l, delta_r)<density[ind]/5.:
                #reject this minimum
                #~ print('REJECT minimum not enought depth')
                local_min_indexes[i] = -1
            
        
        local_min_indexes = local_min_indexes[local_min_indexes!=-1]
        #~ print('local_min_indexes', local_min_indexes, bins[local_min_indexes])
            
            
            
        
        
        #~ nb_over_thresh = np.sum(np.abs(x)>self.threshold)
        sum_cut_density = np.sum(density)
        #~ print('sum_cut_density', sum_cut_density)
        
        if local_min_indexes.size==0:
            labels[:] = 1
            lim = 0
        else:
            #several cut possible
            n_on_left = []
            for ind in local_min_indexes:
                lim = bins[ind]
                n = np.sum(density[bins<=lim])
                n_on_left.append(n)

            n_on_left = np.array(n_on_left)
            #~ print('n_on_left', n_on_left, 'local_min_indexes', local_min_indexes,  x.size)
            #~ p = np.argmin(np.abs(n_on_left-x.size//2))
            #~ p = np.argmin(np.abs(n_on_left-nb_over_thresh//2))
            #~ print(n_on_left)
            #~ print(np.abs(n_on_left-sum_cut_density/2))
            p = np.argmin(np.abs(n_on_left-sum_cut_density/2))
            
            
            #~ print('p', p, n_on_left[p])
            
            #~ print('p', p)
            lim = bins[local_min_indexes[p]]
            #~ print('lim', lim)

        
            if self.peak_sign == '-':
                if np.sum(x<=lim)<=self.nb_min:
                    raise(ValueError)
                    lim = 0
                    labels[:] = 1
                else:
                    labels[x>lim] = 1
            elif self.peak_sign == '+':
                if np.sum(x>=lim)<=self.nb_min:
                    raise(ValueError)
                    labels[:] = 1
                    lim = 0
                else:
                    labels[x<lim] = 1
        
        return labels, lim, bins, density
    
    def split_loop(self):
        cluster_labels = np.zeros(self.waveforms.shape[0], dtype='int64')

        flat_waveforms = self.waveforms.swapaxes(1,2).reshape(self.waveforms.shape[0], -1)
        nan_waveforms = flat_waveforms.copy()
        if self.peak_sign == '-':
            nan_waveforms[nan_waveforms>=-self.threshold] = np.nan
            m = np.min(self.waveforms[:, -self.n_left, :])
            self.bins=np.arange(m,0, self.binsize)
        elif self.peak_sign == '+':
            nan_waveforms[nan_waveforms<=-self.threshold] = np.nan
            m = np.min(self.waveforms[:, -self.n_left, :])
            self.bins=np.arange(0, m, self.binsize)

        print('bins', self.bins[0], '...', self.bins[-1])
        
        
        k = 0
        dim_visited = []
        
        for i in range(self.max_loop):
                    
            nb_remain = np.sum(cluster_labels>=k)
            sel = cluster_labels == k
            nb_working = np.sum(sel)
            print()
            print('i', i, 'k', k, 'nb_remain', nb_remain, 'nb_working', nb_working, {True:'full', False:'partial'}[nb_remain==nb_working])
            
            
            if i!=0 and nb_remain<self.break_nb_remain:
                cluster_labels[sel] = -1
                print('BREAK nb_remain', nb_remain, '<', self.break_nb_remain)
                break
            
            wf_sel = flat_waveforms[sel, :]
            
            if nb_working<self.nb_min:
                print('TRASH: too few')
                cluster_labels[sel] = -1
                k += 1
                dim_visited = []
                continue
            
            med, mad = median_mad(wf_sel)
            
            #~ if np.all(mad<1.6):
                #~ print('ACCEPT: mad<1.6')
                #~ k += 1
                #~ dim_visited = []
                #~ continue

            
            #TODO to converge fastly be more strict here
            if self.peak_sign == '-':
                if nb_remain==nb_working:
                    possible_dim, = np.nonzero(med<0)
                else:
                    possible_dim, = np.nonzero(med<-3.5)
                    #~ print('ICI', len(possible_dim))
            elif self.peak_sign == '+':
                if nb_remain==nb_working:
                    possible_dim, = np.nonzero(med>0)
                else:
                    possible_dim, = np.nonzero(med>3.5)
                    #~ print('ICI', len(possible_dim))
            
            possible_dim = possible_dim[~np.in1d(possible_dim, dim_visited)]
            
            if len(possible_dim)==0:
                print('len(possible_dim)==0')
                if np.sum(cluster_labels>k)>0:
                    k+=1
                    dim_visited = []
                    continue
                else:
                    cluster_labels[sel] = -1
                    print('BREAK no  more dim')
                    break
                
            #strategy1: take max mad
            #~ dim = possible_dim[np.argmax(mad[possible_dim])]
            
            #strategy2: take where bigest nb of devian
            #~ factor = self.threshold
            #~ if self.peak_sign == '-':
                #~ nb_outer = np.sum(wf_sel[:, possible_dim]<(med[possible_dim]-factor*mad[possible_dim]), axis=0)
            #~ elif self.peak_sign == '+':
                #~ nb_outer = np.sum(wf_sel[:, possible_dim]>(med[possible_dim]+factor*mad[possible_dim]), axis=0)
            #~ print('nb_outer', nb_outer.shape, nb_outer, wf_sel.shape, len(possible_dim))
            #~ dim = possible_dim[np.argmax(nb_outer)]
            
            #strategy3: take hiher mean over threshold
            #~ wf_sel2 = wf_sel[:, possible_dim].copy()
            #~ if self.peak_sign == '-':
                #~ wf_sel2[wf_sel2>=-self.threshold] = np.nan
                #~ dim = possible_dim[np.argmin(np.nanmean(wf_sel2, axis=0))]
            #~ elif self.peak_sign == '+':
                #~ raise(NotImplementedError)

            #strategy4: take best percentile 10
            wf_sel2 = wf_sel[:, possible_dim].copy()
            if self.peak_sign == '-':
                #~ print()
                wf_sel2[wf_sel2>=-self.threshold] = np.nan
                per = np.nanpercentile(wf_sel2, 10., axis=0)
                if np.all(np.isnan(per)):
                    k+=1
                    dim_visited = []
                    continue
                    
                #~ per = np.nanmean(wf_sel2, axis=0)
                #~ print(per)
                #~ print(np.nanmin(per), np.nanargmin(per), per[np.nanargmin(per)])
                dim = possible_dim[np.nanargmin(per)]
            elif self.peak_sign == '+':
                raise(NotImplementedError)
            
            
            
            
            
            
            print('dim', dim)
            feat = wf_sel[:, dim]
            labels, lim, bins, density = self.one_cut(feat)

            print('nb0', np.sum(labels==0), 'nb1', np.sum(labels==1))
            
            if self.debug:
            #~ if False:
                
            #~ if False:
                if not os.path.exists('debug_sawchaincut'):
                    os.mkdir('debug_sawchaincut')
                
                if hasattr(self, 'n_cut'):
                    self.n_cut += 1
                else:
                    self.n_cut = 0
                    #~ fig, ax = plt.subplots()
                    #~ ax.plot(np.arange(self.smooth_kernel.size)*self.binsize, self.smooth_kernel)
                    #~ fig.savefig('debug_sawchaincut/smooth_kernel.png')
                
                count, _ = np.histogram(feat, bins=self.bins)
                count = count.astype(float)/np.sum(count)
                
                filename = 'debug_sawchaincut/one_cut {}.png'.format(self.n_cut)
                fig, axs = plt.subplots(nrows=3)

                axs[0].fill_between(np.arange(med.size), med-mad, med+mad, alpha=.5)
                axs[0].plot(np.arange(med.size), med)
                axs[0].set_title(str(wf_sel.shape[0]))
                axs[0].axvline(dim, color='r')
                axs[0].set_ylim(-10, 5)
                
                axs[1].plot(mad)
                axs[1].axvline(dim, color='r')
                axs[1].set_ylim(0,5)
                
                axs[2].plot(self.bins[:-1], count, color='b')
                axs[2].plot(bins, density, color='k')
                axs[2].axvline(lim, color='k')
                axs[2].set_xlim(-80,0.5)
                axs[2].set_ylim(0,max(density)*1.2)
                
                #~ im = axs[3].imshow(density2d.T, cmap='hot', aspect='auto')
                #~ im.set_clim(0, np.max(density2d)/8.)
                
                #~ print(filename)
                fig.savefig(filename)
                
                #~ plt.show()
            
            #~ print(feat[labels==0].size, feat[labels==1].size)
            
            
            
            
            
            if np.sum(labels==0)==0:
                channel_index = dim // self.width
                #~ dim_visited.append(dim)
                dim_visited.extend(range(channel_index*self.width, (channel_index+1)*self.width))
                print('EXPLORE NEW DIM nb0==0 ', flat_waveforms.shape[1], len(dim_visited))
                
                continue

            
            ind, = np.nonzero(sel)
            cluster_labels[cluster_labels>k] += 1#TODO reflechir la dessus!!!
            cluster_labels[ind[labels==1]] += 1

            if np.sum(labels==1)==0:
                print('ACCEPT: nb1==0')
                k+=1
                dim_visited = []
                continue
        
        
        return cluster_labels
    
    
    def merge_loop(self, unmerged_labels):
        cluster_labels = unmerged_labels
        
        labels = np.unique(cluster_labels)
        labels = labels[labels>=0]
        
        #trash too small
        for k in labels:
            nb = np.sum(cluster_labels==k)
            if nb<self.nb_min:
                cluster_labels[cluster_labels==k] = -1
                print('trash', k)
        
        # relabel
        labels = np.unique(cluster_labels)
        labels = labels[labels>=0]
        for l, k in enumerate(labels):
            cluster_labels[cluster_labels==k] = l
        
        labels = np.unique(cluster_labels)
        labels = labels[labels>=0]
        
        #regroup if very high similarity
        #~ flat_waveforms = self.waveforms.swapaxes(1,2).reshape(self.waveforms.shape[0], -1)
        #~ centroids = []
        #~ for k in labels:
            #~ sel = cluster_labels==k
            #~ med = np.median(flat_waveforms[sel], axis=0)
            #~ centroids.append(med)
        #~ centroids = np.array(centroids)
        #~ similarity = sklearn.metrics.pairwise.cosine_similarity(centroids)
        #~ similarity = np.triu(similarity)

        #~ ind0, ind1 = np.nonzero(similarity>self.threshold_similarity)
        #~ keep = ind0!=ind1
        #~ ind0 = ind0[keep]
        #~ ind1 = ind1[keep]
        #~ pairs = list(zip(labels[ind0], labels[ind1]))
        #~ for k1, k2 in pairs:
            #~ cluster_labels[cluster_labels==k2] = k1
        
        #~ fig, ax = plt.subplots()
        #~ im  = ax.matshow(centroids, cmap='viridis', aspect='auto')
        #~ fig.colorbar(im)
        #~ plt.show()
        #~ fig, ax = plt.subplots()
        #~ im  = ax.matshow(similarity, cmap='viridis')
        #~ fig.colorbar(im)
        #~ plt.show()
        
        # relabel
        labels = np.unique(cluster_labels)
        labels = labels[labels>=0]
        for l, k in enumerate(labels):
            cluster_labels[cluster_labels==k] = l
        
        return cluster_labels
    
    def do_the_job(self):
        
        cluster_labels = self.split_loop()
        cluster_labels = self.merge_loop(cluster_labels)
        
        return cluster_labels

    