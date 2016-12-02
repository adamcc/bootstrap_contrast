from scipy.stats import ttest_ind, ttest_1samp, ttest_rel, mannwhitneyu, norm
from collections import OrderedDict
from numpy.random import randint
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from matplotlib.ticker import AutoMinorLocator, MultipleLocator, MaxNLocator, FixedLocator, AutoLocator, FormatStrFormatter
from decimal import Decimal
import matplotlib.pyplot as plt
from matplotlib import rc, rcParams, rcdefaults
import sys
import seaborn as sb
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# This imports the custom functions used.
# These have been places in separate .py files for reduced code clutter.
from .plot_tools import normalizeSwarmY, normalizeContrastY, offsetSwarmX, resetSwarmX, getSwarmSpan
from .plot_tools import align_yaxis, halfviolin, drawback_y, drawback_x
from .bootstrap_tools import ci, bootstrap_indexes, jackknife_indexes, getstatarray, bca

# Taken without modification from scikits.bootstrap package
# Keep python 2/3 compatibility, without using six. At some point,
# we may need to add six as a requirement, but right now we can avoid it.
try:
    xrange
except NameError:
    xrange = range

class InstabilityWarning(UserWarning):
    """Issued when results may be unstable."""
    pass

       
def bootstrap(data, 
              statfunction = None,
              smoothboot = False,
              alpha = 0.05, 
              reps = 3000):
    
    # Taken from scikits.bootstrap code
    # Initialise statfunction
    if statfunction == None:
        statfunction = np.mean
    
    # Compute two-sided alphas.
    alphas = np.array([alpha/2, 1-alpha/2])
    
    # Turns data into array, then tuple.
    data = np.array(data)
    tdata = (data,)

    # The value of the statistic function applied just to the actual data.
    ostat = statfunction(*tdata)
    
    ## Convenience function invoked to get array of desired bootstraps see above!
    # statarray = getstatarray(tdata, statfunction, reps, sort = True)
    statarray = sb.algorithms.bootstrap(data, func = statfunction, n_boot = reps, smooth = smoothboot)
    statarray.sort()

    # Get Percentile indices
    pct_low_high = np.round((reps-1)*alphas)
    pct_low_high = np.nan_to_num(pct_low_high).astype('int')

    # Get Bias-Corrected Accelerated indices convenience function invoked.
    bca_low_high = bca(tdata, alphas, statarray, statfunction, ostat, reps)
    
    # Warnings for unstable or extreme indices.
    for ind in [pct_low_high, bca_low_high]:
        if np.any(ind==0) or np.any(ind==reps-1):
            warnings.warn("Some values used extremal samples results are probably unstable.")
        elif np.any(ind<10) or np.any(ind>=reps-10):
            warnings.warn("Some values used top 10 low/high samples results may be unstable.")
        
    result = OrderedDict()
    result['summary'] = ostat
    result['statistic'] = str(statfunction)
    result['bootstrap_reps'] = reps
    result['pct_ci_low'] = statarray[pct_low_high[0]]
    result['pct_ci_high'] = statarray[pct_low_high[1]]
    result['bca_ci_low'] = statarray[bca_low_high[0]]
    result['bca_ci_high'] = statarray[bca_low_high[1]]
    result['stat_array'] = np.array(statarray)
    result['pct_low_high_indices'] = pct_low_high
    result['bca_low_high_indices'] = bca_low_high
    return result

def bootstrap_contrast(data = None,
                       idx = None,
                       x = None,
                       y = None,
                       statfunction = None,
                       smoothboot = False,
                       alpha = 0.05, 
                       reps = 3000):
    
    # Taken from scikits.bootstrap code
    # Initialise statfunction
    if statfunction == None:
        statfunction = np.mean
    # check if idx was parsed
    if idx == None:
        idx = [0,1]
        
    # Compute two-sided alphas.
    alphas = np.array([alpha/2, 1-alpha/2])
    
    levels = data[x].unique()

    # Two types of dictionaries
    levels_to_idx = dict( zip(list(levels), range(0,len(levels))) ) # levels are the keys.
    idx_to_levels = dict( zip(range(0,len(levels)), list(levels)) ) # level indexes are the keys.
                                                                    # Not sure if I need this latter dict.
    
    # The loop approach below allows us to mix and match level and indices
    # when declaring the idx above.
    arraylist = list() # list to temporarily store the rawdata arrays.
    for i in idx:
        if i in levels_to_idx: # means the supplied id is an actual level
            arraylist.append( np.array(data.ix[data[x] == levels[levels_to_idx[i]]][y]) ) # when I get levels
        elif i in idx_to_levels: # means the supplied id is the level index (does this make sense?)
            arraylist.append( np.array(data.ix[data[x] == levels[i]][y]) ) # when I get level indexes
            
    # Pull out the arrays. 
    # The first array in `arraylist` is the reference array. 
    ref_array = arraylist[0]
    exp_array = arraylist[1]
    
    # Generate statarrays for both arrays.
    ref_statarray = sb.algorithms.bootstrap(ref_array, func = statfunction, n_boot = reps, smooth = smoothboot)
    exp_statarray = sb.algorithms.bootstrap(exp_array, func = statfunction, n_boot = reps, smooth = smoothboot)
    
    diff_array = exp_statarray - ref_statarray
    diff_array_t = (diff_array,) # Note tuple form.
    diff_array.sort()

    # The difference as one would calculate it.
    ostat = statfunction(exp_array) - statfunction(ref_array)
    
    # Get Percentile indices
    pct_low_high = np.round((reps-1)*alphas)
    pct_low_high = np.nan_to_num(pct_low_high).astype('int')

    # Get Bias-Corrected Accelerated indices convenience function invoked.
    bca_low_high = bca(diff_array_t, alphas, diff_array, statfunction, ostat, reps)
    
    # Warnings for unstable or extreme indices.
    for ind in [pct_low_high, bca_low_high]:
        if np.any(ind==0) or np.any(ind==reps-1):
            warnings.warn("Some values used extremal samples results are probably unstable.")
        elif np.any(ind<10) or np.any(ind>=reps-10):
            warnings.warn("Some values used top 10 low/high samples results may be unstable.")
            
    # two-tailed t-test to see if the means of both arrays are different.
    ttestresult = ttest_ind(arraylist[0], arraylist[1])
    
    # Mann-Whitney test to see if the mean of the diff_array is not zero.
    mannwhitneyresult = mannwhitneyu(arraylist[0], arraylist[1])
    
    result = OrderedDict()
    result['summary'] = ostat
    result['statistic'] = str(statfunction)
    result['bootstrap_reps'] = reps
    result['pct_ci_low'] = diff_array[pct_low_high[0]]
    result['pct_ci_high'] = diff_array[pct_low_high[1]]
    result['bca_ci_low'] = diff_array[bca_low_high[0]]
    result['bca_ci_high'] = diff_array[bca_low_high[1]]
    result['diffarray'] = np.array(diff_array)
    result['pct_low_high_indices'] = pct_low_high
    result['bca_low_high_indices'] = bca_low_high
    result['statistic_ref'] = statfunction(ref_array)
    result['statistic_exp'] = statfunction(exp_array)
    result['ref_input'] = arraylist[0]
    result['test_input'] = arraylist[1]
    result['pvalue_ttest'] = ttestresult[1]
    result['pvalue_mannWhitney'] = mannwhitneyresult[1] * 2 # two-sided test result.
    return result

def plotbootstrap(coll, bslist, ax, violinWidth, 
                  violinOffset, marker = 'o', color = 'k', 
                  markerAlpha = 0.75,
                  markersize = None,
                  CiAlpha = 0.75,
                  offset = True,
                  linewidth = 2, 
                  rightspace = 0.2,
                 **kwargs):
    '''subfunction to plot the bootstrapped distribution along with BCa intervals.'''
    if markersize is None:
         mSize = 12.
    else:
        mSize = markersize

    autoxmin = ax.get_xlim()[0]
    x, _ = np.array(coll.get_offsets()).T
    xmax = x.max()

    if offset:
        violinbasex = xmax + violinOffset
    else:
        violinbasex = 1
        
    array = list(bslist.items())[7][1]
    
    v = ax.violinplot(array, [violinbasex], 
                      widths = violinWidth * 2, 
                      showextrema = False, showmeans = False)
    
    for b in v['bodies']:
        m = np.mean(b.get_paths()[0].vertices[:, 0])
        b.get_paths()[0].vertices[:, 0] = np.clip(b.get_paths()[0].vertices[:, 0], m, np.inf)
        b.set_color('k')
    
    # Plot the summary measure.
    ax.plot(violinbasex, bslist['summary'],
             marker = marker,
             markerfacecolor = color, 
             markersize = mSize,
             alpha = markerAlpha
            )

    # Plot the CI.
    ax.plot([violinbasex, violinbasex],
             [bslist['bca_ci_low'], bslist['bca_ci_high']],
             color = color, 
             alpha = CiAlpha,
             linestyle = 'solid'
            )
    
    ax.set_xlim(autoxmin, (violinbasex + violinWidth + rightspace))
    
    if array.min() < 0 < array.min():
        ax.set_ylim(array.min(), array.max())
    elif 0 <= array.min(): 
        ax.set_ylim(0, array.max() * 1.1)
    elif 0 >= array.max():
        ax.set_ylim(array.min() * 1.1, 0)
        
def plotbootstrap_hubspoke(bslist, ax, violinWidth, violinOffset, 
                           marker = 'o', color = 'k', 
                           markerAlpha = 0.75,
                           markersize = None,
                           CiAlpha = 0.75,
                           linewidth = 2,
                          **kwargs):
    
    '''subfunction to plot the bootstrapped distribution along with BCa intervals for hub-spoke plots.'''

    if markersize is None:
        mSize = 12.
    else:
        mSize = markersize

    ylims = list()
    
    for i in range(0, len(bslist)):
        bsi = bslist[i]
        array = list(bsi.items())[7][1] # Pull out the bootstrapped array.
        ylims.append(array)
        
        # Then plot as violinplot.
        v = ax.violinplot(array, [i+1], 
                          widths = violinWidth * 2, 
                          showextrema = False, showmeans = False)
        
        for b in v['bodies']:
            m = np.mean(b.get_paths()[0].vertices[:, 0])
            b.get_paths()[0].vertices[:, 0] = np.clip(b.get_paths()[0].vertices[:, 0], m, np.inf)
            b.set_color('k')
            # Plot the summary measure.
            ax.plot(i+1, bsi['summary'],
                     marker = marker,
                     markerfacecolor = color, 
                     markersize = mSize,
                     alpha = markerAlpha
                    )

            # Plot the CI.
            ax.plot([i+1, i+1],
                     [bsi['bca_ci_low'], bsi['bca_ci_high']],
                     color = color, 
                     alpha = CiAlpha,
                     linestyle = 'solid'
                    )
            
    ylims = np.array(ylims).flatten()
    if ylims.min() < 0 and ylims.max() < 0: # All effect sizes are less than 0.
        ax.set_ylim(1.1 * ylims.min(), 0)
    elif ylims.min() > 0:                   # All effect sizes are more than 0.
        ax.set_ylim(-0.25, 1.1 * ylims.max())
    elif ylims.min() < 0 < ylims.max():     # One or more effect sizes straddle 0.
        ax.set_ylim(1.1 * ylims.min(), 1.1 * ylims.max())

def swarmsummary(data, x, y, idx = None, statfunction = None, 
                 violinOffset = 0.1, violinWidth = 0.2, 
                 figsize = (7,7), legend = True,
                 smoothboot = False,
                 rawMarkerSize = 10,
                 summaryMarkerSize = 12,
                 rawMarkerType = 'o',
                 summaryMarkerType = 'o',
                 **kwargs):
    df = data # so we don't re-order the rawdata!
    # initialise statfunction
    if statfunction == None:
        statfunction = np.mean
        
    # calculate bootstrap list.
    bslist = OrderedDict()

    if idx is None:
        levs = df[x].unique()   # DO NOT USE the numpy.unique() method.
                                # It will not preserve the order of appearance of the levels.
    else:
        levs = idx

    for i in range (0, len(levs)):
        temp_df = df.loc[df[x] == levs[i]]
        bslist[levs[i]] = bootstrap(temp_df[y], statfunction = statfunction, smoothboot = smoothboot)
    
    bsplotlist = list(bslist.items())
    
    # Initialise figure
    #sb.set_style('ticks')
    fig, ax = plt.subplots(figsize = figsize)
    sw = sb.swarmplot(data = df, x = x, y = y, order = levs, 
      size = rawMarkerSize, marker = rawMarkerType, **kwargs)
    y_lims = list()
    
    for i in range(0, len(bslist)):
        plotbootstrap(sw.collections[i], 
                      bslist = bsplotlist[i][1], 
                      ax = ax, 
                      violinWidth = violinWidth, 
                      violinOffset = violinOffset,
                      marker = summaryMarkerType,
                      markersize = summaryMarkerSize,
                      color = 'k', 
                      linewidth = 2)
        
        # Get the y-offsets, save into a list.
        _, y = np.array(sw.collections[i].get_offsets()).T 
        y_lims.append(y)
    
    # Concatenate the list of y-offsets
    y_lims = np.concatenate(y_lims)
    ax.set_ylim(0.9 * y_lims.min(), 1.1 * y_lims.max())
    
    if legend is True:
        ax.legend(loc='center left', bbox_to_anchor=(1.1, 1))
    elif legend is False:
        ax.legend().set_visible(False)
        
    sb.despine(ax = ax, trim = True)
    
    return fig, pd.DataFrame.from_dict(bslist)
    
def contrastplot(data, x, y, idx = None, statfunction = None, reps = 3000,
                 violinOffset = 0.375,
                 violinWidth = 0.2, 
                 lineWidth = 2, 
                 
                 summaryLineWidth = 0.25, 
                 summaryMarkerSize = 10, 
                 summaryMarkerType = 'o',
                 rawMarkerSize = 8,
                 rawMarkerType = 'o',
                 heightRatio = (1, 1), 
                 alpha = 0.75, 
                 barWidth = 0.005, 
                 floatSwarmSpacer = 0.2,

                 showRawData = True,
                 showMeans = True, 
                 summaryLine = True, 
                 summaryBar = False, 
                 showCI = False, 
                 legend = True, 
                 showAllYAxes = False,
                 rawShareY = True, 
                 contrastShareY = True,
                 floatContrast = True,
                 smoothboot = False, 
                 
                 figsize = None, 
                 pal = None,
                 swarmYlim = None, 
                 contrastYlim = None,
                 effectSizeYLabel = "Effect Size", 
                 axis_title_size = None,
                 yticksize = None,
                 xticksize = None,

                 meansColour = 'black', 
                 summaryBarColor = 'grey',
                 meansSummaryLineStyle = 'solid', 
                 contrastZeroLineStyle = 'solid', 
                 contrastEffectSizeLineStyle = 'solid',
                 contrastZeroLineColor = 'black', 
                 contrastEffectSizeLineColor = 'black',

                 **kwargs):

    # Drop all nans.
    data = data.dropna()

    # Set clean style
    sb.set(style = 'ticks')

    # plot params
    if axis_title_size is None:
        axis_title_size = 15
    if yticksize is None:
        yticksize = 12
    if xticksize is None:
        xticksize = 12

    axisTitleParams = {'labelsize' : axis_title_size}
    xtickParams = {'labelsize' : xticksize}
    ytickParams = {'labelsize' : yticksize}

    rc('axes', **axisTitleParams)
    rc('xtick', **xtickParams)
    rc('ytick', **ytickParams)


    # initialise statfunction
    if statfunction == None:
        statfunction = np.mean

    # Ensure summaryLine and summaryBar are not displayed together.
    if summaryLine is True and summaryBar is True:
        summaryBar = True
        summaryLine = False
        
    # Set palette based on total number of categories in data['x'] or data['hue_column']
    if 'hue' in kwargs:
        u = kwargs['hue']
    else:
        u = x
    
    # Here we define the palette on all the levels of the 'x' column.
    # Thus, if the same pandas dataframe is re-used across different plots,
    # the color identity of each group will be maintained.
    if pal is None:
        plotPal = dict( zip( data[u].unique(), sb.color_palette(n_colors = len(data[u].unique())) ) 
                      )
    else:
        plotPal = pal
        
    # Get and set levels of data[x]    
    if idx is None:
        # No idx is given, so all groups are compared to the first one in the DataFrame column.
        levs_tuple = (tuple(data[x].unique()), )
        widthratio = [1]
        if len(data[x].unique()) > 2:
            floatContrast = False
    else:
        # check if multi-plot or not
        if all(isinstance(element, str) for element in idx):
            # if idx is supplied but not a multiplot (ie single list or tuple) 
            levs_tuple = (idx, )
            widthratio = [1]
            if len(idx) > 2:
                floatContrast = False
        elif all(isinstance(element, tuple) for element in idx):
            # if idx is supplied, and it is a list/tuple of tuples or lists, we have a multiplot!
            levs_tuple = idx
            if (any(len(element) > 2 for element in levs_tuple) and floatContrast == True):
                # if any of the tuples in idx has more than 2 groups, we turn set floatContrast as False.
                floatContrast = False
            # Make sure the widthratio of the seperate multiplot corresponds to how 
            # many groups there are in each one.
            widthratio = []
            for i in levs_tuple:
                widthratio.append(len(i))
    u = list()
    for t in levs_tuple:
        for i in np.unique(t):
            u.append(i)
    u = np.unique(u)

    tempdat = data.copy()
    # Make sure the 'x' column is a 'category' type.
    tempdat[x] = tempdat[x].astype("category")
    tempdat = tempdat[tempdat[x].isin(u)]
    # Filters out values that were not specified in idx.
    tempdat[x].cat.set_categories(u, ordered = True, inplace = True)
    if swarmYlim is None:
        swarm_ylim = np.array([np.min(tempdat[y]), np.max(tempdat[y])])
    else:
        swarm_ylim = np.array([swarmYlim[0],swarmYlim[1]])

    if contrastYlim is not None:
        contrastYlim = np.array([contrastYlim[0],contrastYlim[1]])

    # Expand the ylim in both directions.
    ## Find half of the range of swarm_ylim.
    swarmrange = swarm_ylim[1] - swarm_ylim[0]
    pad = 0.1 * swarmrange
    x2 = np.array([swarm_ylim[0]-pad, swarm_ylim[1]+pad])
    swarm_ylim = x2
    
    # Create list to collect all the contrast DataFrames generated.
    contrastList = list()
    contrastListNames = list()
    
    if figsize is None:
        if len(levs_tuple) > 2:
            figsize = (12,(12/np.sqrt(2)))
        else:
            figsize = (8,(8/np.sqrt(2)))


    if showRawData is True:
        maxSwarmSpan = 0.25
    else:
        maxSwarmSpan = barWidth         
        
    # Initialise figure, taking into account desired figsize.
    fig = plt.figure(figsize = figsize)
    
    # Initialise GridSpec based on `levs_tuple` shape.
    gsMain = gridspec.GridSpec( 1, np.shape(levs_tuple)[0], # 1 row; columns based on number of tuples in tuple.
                               width_ratios = widthratio ) 
    
    for gsIdx, levs in enumerate(levs_tuple):
        # Create temp copy of the data for plotting!
        plotdat = data.copy()
        
        # Make sure the 'x' column is a 'category' type.
        plotdat[x] = plotdat[x].astype("category")
        plotdat = plotdat[plotdat[x].isin(levs)]
        plotdat[x].cat.set_categories(levs, ordered = True, inplace = True)
        
        # then order according to `levs`!
        plotdat.sort_values(by = [x])
        
        # Calculate means
        means = plotdat.groupby([x], sort = True).mean()[y]
        # # Calculate medians
        # medians = plotdat.groupby([x], sort = True).median()[y]

        if len(levs) == 2:            
            # Calculate bootstrap contrast. 
            tempbs = bootstrap_contrast(data = data, 
                                        x = x, 
                                        y = y,
                                        idx = levs, 
                                        statfunction = statfunction, 
                                        smoothboot = smoothboot,
                                        reps = reps)
            
            contrastListNames.append( str(levs[1]) + " v.s " + str(levs[0]) )
            contrastList.append(tempbs)

            if floatContrast is True:
                ax_left = fig.add_subplot(gsMain[gsIdx], frame_on = False) 
                # Use fig.add_subplot instead of plt.Subplot
                
                if showRawData is True:
                    # Plot the raw data as a swarmplot.
                    sw = sb.swarmplot(data = plotdat, x = x, y = y, 
                                      order = levs, ax = ax_left, 
                                      alpha = alpha, palette = plotPal,
                                      size = rawMarkerSize,
                                      marker = rawMarkerType,
                                      **kwargs)
                    sw.set_ylim(swarm_ylim)
                
                maxXBefore = max(sw.collections[0].get_offsets().T[0])
                minXAfter = min(sw.collections[1].get_offsets().T[0])

                xposAfter = maxXBefore + floatSwarmSpacer
                xAfterShift = minXAfter - xposAfter
                offsetSwarmX(sw.collections[1], -xAfterShift)

                if summaryBar is True:
                    bar_raw = sb.barplot(x = means.index, 
                        y = means.values, 
                        facecolor = summaryBarColor, 
                        ax = ax_left, 
                        alpha = 0.25)
                    ## get swarm with largest span, set as max width of each barplot.
                    for i, bar in enumerate(bar_raw.patches):
                        x_width = bar.get_x()
                        width = bar.get_width()
                        centre = x_width + width/2.
                        if i == 0:
                            bar.set_x(centre - maxSwarmSpan/2.)
                        else:
                            bar.set_x(centre - xAfterShift - maxSwarmSpan/2.)
                        bar.set_width(maxSwarmSpan)
                
                ## Set the ticks locations for ax_left.
                axLeftLab = ax_left.get_xaxis().get_ticklabels
                ax_left.get_xaxis().set_ticks((0, xposAfter))
                ## Set the tick labels!
                ax_left.set_xticklabels([ax_left.get_xaxis().get_ticklabels()[0].get_text(),
                                         ax_left.get_xaxis().get_ticklabels()[1].get_text()],
                                       rotation = 45,
                                       horizontalalignment = 'right')
                ## Remove left axes x-axis title.
                ax_left.set_xlabel("")

                # Set up floating axis on right.
                ax_right = ax_left.twinx()

                # Then plot the bootstrap
                # We should only be looking at sw.collections[1],
                # as contrast plots will only be floating in this condition.
                plotbootstrap(sw.collections[1],
                              bslist = tempbs, 
                              ax = ax_right,
                              violinWidth = violinWidth, 
                              violinOffset = violinOffset,
                              markersize = summaryMarkerSize,
                              marker = summaryMarkerType,
                              color = 'k', 
                              linewidth = 2)

                # Set reference lines
                ## First get leftmost limit of left reference group
                xtemp, _ = np.array(sw.collections[0].get_offsets()).T
                leftxlim = xtemp.min()
                ## Then get leftmost limit of right test group
                xtemp, _ = np.array(sw.collections[1].get_offsets()).T
                rightxlim = xtemp.min()

                ## zero line
                ax_right.hlines(0,                   # y-coordinates
                                leftxlim, 3.5,       # x-coordinates, start and end.
                                linestyle = contrastZeroLineStyle,
                                linewidth = 0.75,
                                color = contrastZeroLineColor)

                ## effect size line
                ax_right.hlines(tempbs['summary'], 
                                rightxlim, 3.5,        # x-coordinates, start and end.
                                linestyle = contrastEffectSizeLineStyle,
                                linewidth = 0.75,
                                color = contrastEffectSizeLineColor)

                
                ## If the effect size is positive, shift the right axis up.
                if float(tempbs['summary']) > 0:
                    rightmin = ax_left.get_ylim()[0] - float(tempbs['summary'])
                    rightmax = ax_left.get_ylim()[1] - float(tempbs['summary'])
                ## If the effect size is negative, shift the right axis down.
                elif float(tempbs['summary']) < 0:
                    rightmin = ax_left.get_ylim()[0] + float(tempbs['summary'])
                    rightmax = ax_left.get_ylim()[1] + float(tempbs['summary'])

                ax_right.set_ylim(rightmin, rightmax)

                if legend is True:
                    ax_left.legend(loc='center left', bbox_to_anchor=(1.1, 1))
                elif legend is False:
                    ax_left.legend().set_visible(False)
                    
                if gsIdx > 0:
                    ax_right.set_ylabel('')

                align_yaxis(ax_left, tempbs['statistic_ref'], ax_right, 0.)

            elif floatContrast is False:
                # Create subGridSpec with 2 rows and 1 column.
                gsSubGridSpec = gridspec.GridSpecFromSubplotSpec(2, 1, 
                                                                 subplot_spec = gsMain[gsIdx])
                ax_top = plt.Subplot(fig, gsSubGridSpec[0, 0], frame_on = False)

                if showCI is True:
                    sb.barplot(data = plotdat, x = x, y = y, ax = ax_top, alpha = 0, ci = 95)

                # Plot the swarmplot on the top axes.
                sw = sb.swarmplot(data = plotdat, x = x, y = y, 
                                  order = levs, ax = ax_top, 
                                  alpha = alpha, palette = plotPal,
                                  size = rawMarkerSize,
                                  marker = rawMarkerType,
                                  **kwargs)
                sw.set_ylim(swarm_ylim)

                # Then plot the summary lines.
                if showMeans is True:
                    if summaryLine is True:
                        for i, m in enumerate(means):
                            ax_top.plot((i - summaryLineWidth, i + summaryLineWidth),           # x-coordinates
                                        (m, m),                                                 # y-coordinates
                                        color = meansColour, linestyle = meansSummaryLineStyle)
                    elif summaryBar is True:
                        sb.barplot(x = means.index, 
                            y = means.values, 
                            facecolor = summaryBarColor, 
                            ax = ax_top, 
                            alpha = 0.25)

                # if showMedians is True:
                #     if summaryLine is True:
                #         for i, m in enumerate(medians):
                #             ax_top.plot((i - summaryLineWidth, i + summaryLineWidth), 
                #                         (m, m), 
                #                         color = mediansColour, linestyle = mediansSummaryLineStyle)
                #     elif summaryBar is True:
                #         sb.barplot(x = medians.index, 
                #             y = medians.values, 
                #             facecolor = summaryBarColor, 
                #             ax = ax_top, 
                #             alpha = 0.25)
                        
                if legend is True:
                    ax_top.legend(loc='center left', bbox_to_anchor=(1.1, 1))
                elif legend is False:
                    ax_top.legend().set_visible(False)
                    
                fig.add_subplot(ax_top)
                ax_top.set_xlabel('')
                
                # Initialise bottom axes
                ax_bottom = plt.Subplot(fig, gsSubGridSpec[1, 0], sharex = ax_top, frame_on = False)

                # Plot the CIs on the bottom axes.
                plotbootstrap(sw.collections[1],
                              bslist = tempbs,
                              ax = ax_bottom, 
                              violinWidth = violinWidth,
                              markersize = summaryMarkerSize,
                              marker = summaryMarkerType,
                              offset = False,
                              violinOffset = 0,
                              linewidth = 2)

                # Set bottom axes ybounds
                if contrastYlim is not None:
                #     ax_bottom.set_ylim( tempbs['diffarray'].min(), tempbs['diffarray'].max() )
                # else:
                    ax_bottom.set_ylim(contrastYlim)
                
                # Set xlims so everything is properly visible!
                swarm_xbounds = ax_top.get_xbound()
                ax_bottom.set_xbound(swarm_xbounds[0] - (summaryLineWidth * 1.1), 
                                     swarm_xbounds[1] + (summaryLineWidth * 1.))
                
                fig.add_subplot(ax_bottom)

                # Hide the labels for non leftmost plots.
                if gsIdx > 0:
                    ax_top.set_ylabel('')
                    ax_bottom.set_ylabel('')
                    
        elif len(levs) > 2:
            bscontrast = list()
            # Create subGridSpec with 2 rows and 1 column.
            gsSubGridSpec = gridspec.GridSpecFromSubplotSpec(2, 1, 
                                                     subplot_spec = gsMain[gsIdx])
                        
            # Calculate the hub-and-spoke bootstrap contrast.
            for i in range (1, len(levs)): # Note that you start from one. No need to do auto-contrast!
                tempbs = bootstrap_contrast(data = data,
                                            x = x, 
                                            y = y, 
                                            idx = [levs[0], levs[i]],
                                            statfunction = statfunction, 
                                            smoothboot = smoothboot,
                                            reps = reps)
                bscontrast.append(tempbs)
                contrastList.append(tempbs)
                contrastListNames.append(levs[i] + ' vs. ' + levs[0])

            # Initialize the top swarmplot axes.
            ax_top = plt.Subplot(fig, gsSubGridSpec[0, 0], frame_on = False)
            
            if showCI is True:
                sb.barplot(data = plotdat, x = x, y = y, ax = ax_top, alpha = 0, ci = 95)

            sw = sb.swarmplot(data = plotdat, x = x, y = y, 
                              order = levs, ax = ax_top, 
                              alpha = alpha, palette = plotPal,
                              size = rawMarkerSize,
                              marker = rawMarkerType,
                              **kwargs)
            sw.set_ylim(swarm_ylim)

            # Then plot the summary lines.
            if showMeans is True:
                if summaryLine is True:
                    for i, m in enumerate(means):
                        ax_top.plot((i - summaryLineWidth, i + summaryLineWidth),           # x-coordinates
                                    (m, m),                                                 # y-coordinates
                                    color = meansColour, linestyle = meansSummaryLineStyle)
                elif summaryBar is True:
                    sb.barplot(x = means.index, 
                        y = means.values, 
                        facecolor = summaryBarColor, 
                        ax = ax_top, 
                        alpha = 0.25)

            # if showMedians is True:
            #     if summaryLine is True:
            #         for i, m in enumerate(medians):
            #             ax_top.plot((i - summaryLineWidth, i + summaryLineWidth), 
            #                         (m, m), 
            #                         color = mediansColour, linestyle = mediansSummaryLineStyle)
            #     elif summaryBar is True:
            #         sb.barplot(x = medians.index, 
            #             y = medians.values, 
            #             facecolor = summaryBarColor, 
            #             ax = ax_top, 
            #             alpha = 0.25)

            if legend is True:
                ax_top.legend(loc='center left', bbox_to_anchor=(1.1, 1))
            elif legend is False:
                ax_top.legend().set_visible(False)
            
            fig.add_subplot(ax_top)
            ax_top.set_xlabel('')

            # Initialise the bottom swarmplot axes.
            ax_bottom = plt.Subplot(fig, gsSubGridSpec[1, 0], sharex = ax_top, frame_on = False)

            # Plot the CIs on the bottom axes.
            plotbootstrap_hubspoke(bslist = bscontrast,
                                   ax = ax_bottom, 
                                   violinWidth = violinWidth,
                                   violinOffset = violinOffset,
                                   markersize = summaryMarkerSize,
                                   marker = summaryMarkerType,
                                   linewidth = lineWidth)
            # Set bottom axes ybounds
            if contrastYlim is not None:
                ax_bottom.set_ybound(contrastYlim)
            
            # Set xlims so everything is properly visible!
            swarm_xbounds = ax_top.get_xbound()
            ax_bottom.set_xbound(swarm_xbounds[0] - (summaryLineWidth * 1.1), 
                                 swarm_xbounds[1] + (summaryLineWidth * 1.))
            
            # Label the bottom y-axis
            fig.add_subplot(ax_bottom)
            ax_bottom.set_ylabel(effectSizeYLabel)
            
            if gsIdx > 0:
                ax_top.set_ylabel('')
                ax_bottom.set_ylabel('')
            
    # Turn contrastList into a pandas DataFrame,
    contrastList = pd.DataFrame(contrastList).T
    contrastList.columns = contrastListNames
    
    for j,i in enumerate(range(1, len(fig.get_axes()), 2)):

        if floatContrast is False:
            # Draw zero reference line.
            fig.get_axes()[i].hlines(y = 0,
                xmin = fig.get_axes()[i].get_xaxis().get_view_interval()[0], 
                xmax = fig.get_axes()[i].get_xaxis().get_view_interval()[1],
                linestyle = contrastZeroLineStyle,
                linewidth = 0.75,
                color = contrastZeroLineColor)

            sb.despine(ax = fig.get_axes()[i], 
                top = True, right = True, 
                left = False, bottom = True, 
                trim = True)

            if len(fig.get_axes()) == 2:
                # Draw back the lines for the relevant y-axes.
                drawback_y(fig.get_axes()[i])

                # Draw back the lines for the relevant x-axes.
                drawback_x(fig.get_axes()[i])

        else:
            # Re-draw the floating axis to the correct limits.
            ## Get the 'correct limits':
            lower = np.min( contrastList.ix['diffarray',j] )
            upper = np.max( contrastList.ix['diffarray',j] )
            meandiff = contrastList.ix['summary', j]

            ## Make sure we have zero in the limits.
            if lower > 0:
                lower = 0.
            if upper < 0:
                upper = 0.

            ## Get the tick interval from the left y-axis.
            leftticks = fig.get_axes()[i-1].get_yticks()
            tickstep = leftticks[1] - leftticks[0]

            ## First re-draw of axis with new tick interval
            fig.get_axes()[i].yaxis.set_major_locator(MultipleLocator(base = tickstep))
            newticks1 = fig.get_axes()[i].get_yticks()

            ## Obtain major ticks that comfortably encompass lower and upper.
            newticks2 = list()
            for a,b in enumerate(newticks1):
                if (b >= lower and b <= upper):
                    # if the tick lies within upper and lower, take it.
                    newticks2.append(b)
            # if the meandiff falls outside of the newticks2 set, add a tick in the right direction.
            if np.max(newticks2) < meandiff:
                ind = np.where(newticks1 == np.max(newticks2))[0][0] # find out the max tick index in newticks1.
                newticks2.append( newticks1[ind+1] )
            elif meandiff < np.min(newticks2):
                ind = np.where(newticks1 == np.min(newticks2))[0][0] # find out the min tick index in newticks1.
                newticks2.append( newticks1[ind-1] )
            newticks2 = np.array(newticks2)
            newticks2.sort()

            ## Second re-draw of axis to shrink it to desired limits.
            fig.get_axes()[i].yaxis.set_major_locator(FixedLocator(locs = newticks2))
            
            # ## Obtain minor ticks that fall within the major ticks.
            # majorticks = fig.get_axes()[i].yaxis.get_majorticklocs()
            # oldminorticks = fig.get_axes()[i].yaxis.get_minorticklocs()

            ## Despine, trim, and redraw the lines.
            sb.despine(ax = fig.get_axes()[i], trim = True, 
                bottom = False, right = False,
                left = True, top = True)

    for i in range(0, len(fig.get_axes()), 2):

        if i != len(fig.get_axes()) - 2 and 'hue' in kwargs:
            # If this is not the final swarmplot, remove the hue legend.
            fig.get_axes()[i].legend().set_visible(False)

        if floatContrast is True:
            sb.despine(ax = fig.get_axes()[i], trim = True, right = True)
        else:
            sb.despine(ax = fig.get_axes()[i], trim = True, bottom = True, right = True)
            fig.get_axes()[i].get_xaxis().set_visible(False)

        if (showAllYAxes is False and i in range( 2, len(fig.get_axes())) ):
            fig.get_axes()[i].get_yaxis().set_visible(showAllYAxes)
        else:
            # Draw back the lines for the relevant y-axes.
            drawback_y(fig.get_axes()[i])

        if summaryBar is True:
            fig.get_axes()[i].add_artist(Line2D(
                (fig.get_axes()[i].xaxis.get_view_interval()[0], 
                    fig.get_axes()[i].xaxis.get_view_interval()[1]), 
                (0,0),
                color='black', linewidth=0.75
                )
            )

    # Normalize bottom/right axes to each other for Cummings hub-and-spoke plots.
    if (len(fig.get_axes()) > 2 and 
      contrastShareY is True and 
      floatContrast is False):

        # Set contrast ylim as max ticks of leftmost swarm axes.
        if contrastYlim is None:
          contrastYmin = fig.axes[1].yaxis.get_ticklocs()[0]
          contrastYmax = fig.axes[1].yaxis.get_ticklocs()[-1]

        normalizeContrastY(fig, 
            con = contrastList, 
            contrast_ylim = contrastYlim, 
            show_all_yaxes = showAllYAxes)

    if rawShareY is False:
        for i in range(0, len(fig.get_axes()), 2):
            drawback_y(fig.get_axes()[i])
                       
    if contrastShareY is False:
        for i in range(1, len(fig.get_axes()), 2):
            if floatContrast is True:
                sb.despine(ax = fig.get_axes()[i], 
                           top = True, right = False, left = True, bottom = True, 
                           trim = True)
            else:
                sb.despine(ax = fig.get_axes()[i], trim = True)

    # Zero gaps between plots on the same row, if floatContrast is False
    if (floatContrast is False and showAllYAxes is False):
        gsMain.update(wspace = 0)
    else:    
        # Tight Layout!
        gsMain.tight_layout(fig)
    
    # And we're all done.
    rcdefaults() # restore matplotlib defaults.
    sb.set() # restore seaborn defaults.
    return fig, contrastList

def pairedcontrast(data, x, y, idcol, reps = 3000,
    statfunction = None, idx = None, figsize = None,
    beforeAfterSpacer = 0.01, 
    violinWidth = 0.005, 
    floatOffset = 0.05, 
    showRawData = False,
    showAllYAxes = False,
    floatContrast = True,
    smoothboot = False,
    floatViolinOffset = None, 
    showConnections = True,
    summaryBar = False,
    contrastYlim = None,
    swarmYlim = None,
    barWidth = 0.005,
    rawMarkerSize = 8,
    rawMarkerType = 'o',
    summaryMarkerSize = 10,
    summaryMarkerType = 'o',
    summaryBarColor = 'grey',
    meansSummaryLineStyle = 'solid', 
    contrastZeroLineStyle = 'solid', contrastEffectSizeLineStyle = 'solid',
    contrastZeroLineColor = 'black', contrastEffectSizeLineColor = 'black',
    pal = None,
    legendLoc = 2, legendFontSize = 12, legendMarkerScale = 1,
    axis_title_size = None,
    yticksize = None,
    xticksize = None, 
    **kwargs):

    # Preliminaries.
    data = data.dropna()

    # plot params
    if axis_title_size is None:
        axis_title_size = 15
    if yticksize is None:
        yticksize = 12
    if xticksize is None:
        xticksize = 12

    axisTitleParams = {'labelsize' : axis_title_size}
    xtickParams = {'labelsize' : xticksize}
    ytickParams = {'labelsize' : yticksize}

    rc('axes', **axisTitleParams)
    rc('xtick', **xtickParams)
    rc('ytick', **ytickParams)

    ## If `idx` is not specified, just take the FIRST TWO levels alphabetically.
    if idx is None:
        idx = tuple(np.unique(data[x])[0:2],)
    else:
        # check if multi-plot or not
        if all(isinstance(element, str) for element in idx):
            # if idx is supplied but not a multiplot (ie single list or tuple)
            if len(idx) != 2:
                print(idx, "does not have length 2.")
                sys.exit(0)
            else:
                idx = (tuple(idx, ),)
        elif all(isinstance(element, tuple) for element in idx):
            # if idx is supplied, and it is a list/tuple of tuples or lists, we have a multiplot!
            if ( any(len(element) != 2 for element in idx) ):
                # If any of the tuples contain more than 2 elements.
                print(element, "does not have length 2.")
                sys.exit(0)
    if floatViolinOffset is None:
        floatViolinOffset = beforeAfterSpacer/2
    if contrastYlim is not None:
        contrastYlim = np.array([contrastYlim[0],contrastYlim[1]])
    if swarmYlim is not None:
        swarmYlim = np.array([swarmYlim[0],swarmYlim[1]])

    ## Here we define the palette on all the levels of the 'x' column.
    ## Thus, if the same pandas dataframe is re-used across different plots,
    ## the color identity of each group will be maintained.
    ## Set palette based on total number of categories in data['x'] or data['hue_column']
    if 'hue' in kwargs:
        u = kwargs['hue']
    else:
        u = x
    if ('color' not in kwargs and 'hue' not in kwargs):
        kwargs['color'] = 'k'

    if pal is None:
        pal = dict( zip( data[u].unique(), sb.color_palette(n_colors = len(data[u].unique())) ) 
                      )
    else:
        pal = pal

    # Initialise figure.
    if figsize is None:
        if len(idx) > 2:
            figsize = (12,(12/np.sqrt(2)))
        else:
            figsize = (6,6)
    fig = plt.figure(figsize = figsize)

    # Initialise GridSpec based on `levs_tuple` shape.
    gsMain = gridspec.GridSpec( 1, np.shape(idx)[0]) # 1 row; columns based on number of tuples in tuple.
    # Set default statfunction
    if statfunction is None:
        statfunction = np.mean
    # Create list to collect all the contrast DataFrames generated.
    contrastList = list()
    contrastListNames = list()

    for gsIdx, xlevs in enumerate(idx):
        ## Pivot tempdat to get before and after lines.
        data_pivot = data.pivot_table(index = idcol, columns = x, values = y)

        # Start plotting!!
        if floatContrast is True:
            ax_raw = fig.add_subplot(gsMain[gsIdx], frame_on = False)
            ax_contrast = ax_raw.twinx()
        else:
            gsSubGridSpec = gridspec.GridSpecFromSubplotSpec(2, 1, subplot_spec = gsMain[gsIdx])
            ax_raw = plt.Subplot(fig, gsSubGridSpec[0, 0], frame_on = False)
            ax_contrast = plt.Subplot(fig, gsSubGridSpec[1, 0], sharex = ax_raw, frame_on = False)

        ## Plot raw data as swarmplot or stripplot.
        if showRawData is True:
            swarm_raw = sb.swarmplot(data = data, 
                                     x = x, y = y, 
                                     order = xlevs,
                                     ax = ax_raw,
                                     palette = pal,
                                     size = rawMarkerSize,
                                     marker = rawMarkerType,
                                     **kwargs)
        else:
            swarm_raw = sb.stripplot(data = data, 
                                     x = x, y = y, 
                                     order = xlevs,
                                     ax = ax_raw,
                                     palette = pal,
                                     **kwargs)
        swarm_raw.set_ylim(swarmYlim)
           
        ## Get some details about the raw data.
        maxXBefore = max(swarm_raw.collections[0].get_offsets().T[0])
        minXAfter = min(swarm_raw.collections[1].get_offsets().T[0])
        if showRawData is True:
            #beforeAfterSpacer = (getSwarmSpan(swarm_raw, 0) + getSwarmSpan(swarm_raw, 1))/2
            beforeAfterSpacer = 1
        xposAfter = maxXBefore + beforeAfterSpacer
        xAfterShift = minXAfter - xposAfter

        ## shift the after swarmpoints closer for aesthetic purposes.
        offsetSwarmX(swarm_raw.collections[1], -xAfterShift)

        ## pandas DataFrame of 'before' group
        x1 = pd.DataFrame({str(xlevs[0] + '_x') : pd.Series(swarm_raw.collections[0].get_offsets().T[0]),
                       xlevs[0] : pd.Series(swarm_raw.collections[0].get_offsets().T[1]),
                       '_R_' : pd.Series(swarm_raw.collections[0].get_facecolors().T[0]),
                       '_G_' : pd.Series(swarm_raw.collections[0].get_facecolors().T[1]),
                       '_B_' : pd.Series(swarm_raw.collections[0].get_facecolors().T[2]),
                      })
        ## join the RGB columns into a tuple, then assign to a column.
        x1['_hue_'] = x1[['_R_', '_G_', '_B_']].apply(tuple, axis=1) 
        x1 = x1.sort_values(by = xlevs[0])
        x1.index = data_pivot.sort_values(by = xlevs[0]).index

        ## pandas DataFrame of 'after' group
        ### create convenient signifiers for column names.
        befX = str(xlevs[0] + '_x')
        aftX = str(xlevs[1] + '_x')

        x2 = pd.DataFrame( {aftX : pd.Series(swarm_raw.collections[1].get_offsets().T[0]),
            xlevs[1] : pd.Series(swarm_raw.collections[1].get_offsets().T[1])} )
        x2 = x2.sort_values(by = xlevs[1])
        x2.index = data_pivot.sort_values(by = xlevs[1]).index

        ## Join x1 and x2, on both their indexes.
        plotPoints = x1.merge(x2, left_index = True, right_index = True, how='outer')

        ## Add the hue column if hue argument was passed.
        if 'hue' in kwargs:
            h = kwargs['hue']
            plotPoints[h] = data.pivot(index = idcol, columns = x, values = h)[xlevs[0]]
            swarm_raw.legend(loc = legendLoc, 
                fontsize = legendFontSize, 
                markerscale = legendMarkerScale)

        ## Plot the lines to join the 'before' points to their respective 'after' points.
        if showConnections is True:
            for i in plotPoints.index:
                ax_raw.plot([ plotPoints.ix[i, befX],
                    plotPoints.ix[i, aftX] ],
                    [ plotPoints.ix[i, xlevs[0]], 
                    plotPoints.ix[i, xlevs[1]] ],
                    linestyle = 'solid',
                    color = plotPoints.ix[i, '_hue_'],
                    linewidth = 0.75,
                    alpha = 0.75
                    )

        ## Hide the raw swarmplot data if so desired.
        if showRawData is False:
            swarm_raw.collections[0].set_visible(False)
            swarm_raw.collections[1].set_visible(False)

        if showRawData is True:
            #maxSwarmSpan = max(np.array([getSwarmSpan(swarm_raw, 0), getSwarmSpan(swarm_raw, 1)]))/2
            maxSwarmSpan = 0.5
        else:
            maxSwarmSpan = barWidth            

        ## Plot Summary Bar.
        if summaryBar is True:
            # Calculate means
            means = data.groupby([x], sort = True).mean()[y]
            # # Calculate medians
            # medians = data.groupby([x], sort = True).median()[y]

            ## Draw summary bar.
            bar_raw = sb.barplot(x = means.index, 
                        y = means.values, 
                        order = xlevs,
                        ax = ax_raw,
                        ci = 0,
                        facecolor = summaryBarColor, 
                        alpha = 0.25)
            ## Draw zero reference line.
            ax_raw.add_artist(Line2D(
                (ax_raw.xaxis.get_view_interval()[0], 
                    ax_raw.xaxis.get_view_interval()[1]), 
                (0,0),
                color='black', linewidth=0.75
                )
            )       

            ## get swarm with largest span, set as max width of each barplot.
            for i, bar in enumerate(bar_raw.patches):
                x_width = bar.get_x()
                width = bar.get_width()
                centre = x_width + width/2.
                if i == 0:
                    bar.set_x(centre - maxSwarmSpan/2.)
                else:
                    bar.set_x(centre - xAfterShift - maxSwarmSpan/2.)
                bar.set_width(maxSwarmSpan)

        # Get y-limits of the treatment swarm points.
        beforeRaw = pd.DataFrame( swarm_raw.collections[0].get_offsets() )
        afterRaw = pd.DataFrame( swarm_raw.collections[1].get_offsets() )
        before_leftx = min(beforeRaw[0])
        after_leftx = min(afterRaw[0])
        after_rightx = max(afterRaw[0])
        after_stat_summary = statfunction(beforeRaw[1])

        # Calculate the summary difference and CI.
        plotPoints['delta_y'] = plotPoints[xlevs[1]] - plotPoints[xlevs[0]]
        plotPoints['delta_x'] = [0] * np.shape(plotPoints)[0]

        tempseries = plotPoints['delta_y'].tolist()
        test = tempseries.count(tempseries[0]) != len(tempseries)

        bootsDelta = bootstrap(plotPoints['delta_y'],
            statfunction = statfunction, 
            smoothboot = smoothboot,
            reps = reps)
        summDelta = bootsDelta['summary']
        lowDelta = bootsDelta['bca_ci_low']
        highDelta = bootsDelta['bca_ci_high']

        # set new xpos for delta violin.
        if floatContrast is True:
            if showRawData is False:
                xposPlusViolin = deltaSwarmX = after_rightx + floatViolinOffset
            else:
                xposPlusViolin = deltaSwarmX = after_rightx + maxSwarmSpan
        else:
            xposPlusViolin = xposAfter
        if showRawData is True:
            # If showRawData is True and floatContrast is True, 
            # set violinwidth to the barwidth.
            violinWidth = maxSwarmSpan

        xmaxPlot = xposPlusViolin + violinWidth

        # Plot the summary measure.
        ax_contrast.plot(xposPlusViolin, summDelta,
            marker = 'o',
            markerfacecolor = 'k', 
            markersize = summaryMarkerSize,
            alpha = 0.75
            )

        # Plot the CI.
        ax_contrast.plot([xposPlusViolin, xposPlusViolin],
            [lowDelta, highDelta],
            color = 'k', 
            alpha = 0.75,
            linestyle = 'solid'
            )

        # Plot the violin-plot.
        v = ax_contrast.violinplot(bootsDelta['stat_array'], [xposPlusViolin], 
                                 widths = violinWidth, 
                                 showextrema = False, 
                                 showmeans = False)
        halfviolin(v, half = 'right', color = 'k')

        # Remove left axes x-axis title.
        ax_raw.set_xlabel("")
        # Remove floating axes y-axis title.
        ax_contrast.set_ylabel("")

        # Set proper x-limits
        ax_raw.set_xlim(before_leftx - beforeAfterSpacer/2, xmaxPlot)
        ax_raw.get_xaxis().set_view_interval(before_leftx - beforeAfterSpacer/2, 
            after_rightx + beforeAfterSpacer/2)
        ax_contrast.set_xlim(ax_raw.get_xlim())

        if floatContrast is True:
            # Set the ticks locations for ax_raw.
            ax_raw.get_xaxis().set_ticks((0, xposAfter))

            # Make sure they have the same y-limits.
            ax_contrast.set_ylim(ax_raw.get_ylim())
            
            # Drawing in the x-axis for ax_raw.
            ## Set the tick labels!
            ax_raw.set_xticklabels(xlevs, rotation = 45, horizontalalignment = 'right')
            ## Get lowest y-value for ax_raw.
            y = ax_raw.get_yaxis().get_view_interval()[0] 

            # Align the left axes and the floating axes.
            align_yaxis(ax_raw, statfunction(plotPoints[xlevs[0]]),
                           ax_contrast, 0)

            # Add label to floating axes. But on ax_raw!
            ax_raw.text(x = deltaSwarmX,
                          y = ax_raw.get_yaxis().get_view_interval()[0],
                          horizontalalignment = 'left',
                          s = 'Difference',
                          fontsize = 15)        

            # Set reference lines
            ## zero line
            ax_contrast.hlines(0,                                           # y-coordinate
                            ax_contrast.xaxis.get_majorticklocs()[0],       # x-coordinates, start and end.
                            ax_raw.xaxis.get_view_interval()[1],   
                            linestyle = 'solid',
                            linewidth = 0.75,
                            color = 'black')

            ## effect size line
            ax_contrast.hlines(summDelta, 
                            ax_contrast.xaxis.get_majorticklocs()[1],
                            ax_raw.xaxis.get_view_interval()[1],
                            linestyle = 'solid',
                            linewidth = 0.75,
                            color = 'black')

            # Align the left axes and the floating axes.
            align_yaxis(ax_raw, after_stat_summary, ax_contrast, 0.)
        else:
            # Set the ticks locations for ax_raw.
            ax_raw.get_xaxis().set_ticks((0, xposAfter))
            
            fig.add_subplot(ax_raw)
            fig.add_subplot(ax_contrast)
        ax_contrast.set_ylim(contrastYlim)
        # Calculate p-values.
        # 1-sample t-test to see if the mean of the difference is different from 0.
        ttestresult = ttest_1samp(plotPoints['delta_y'], popmean = 0)[1]
        bootsDelta['ttest_pval'] = ttestresult
        contrastList.append(bootsDelta)
        contrastListNames.append( str(xlevs[1])+' v.s. '+str(xlevs[0]) )

    # Turn contrastList into a pandas DataFrame,
    contrastList = pd.DataFrame(contrastList).T
    contrastList.columns = contrastListNames

    # Now we iterate thru the contrast axes to normalize all the ylims.
    for j,i in enumerate(range(1, len(fig.get_axes()), 2)):

        ## Get max and min of the dataset.
        lower = np.min(contrastList.ix['stat_array',j])
        upper = np.max(contrastList.ix['stat_array',j])
        meandiff = contrastList.ix['summary', j]

        ## Make sure we have zero in the limits.
        if lower > 0:
            lower = 0.
        if upper < 0:
            upper = 0.

        ## Get tick distance on raw axes.
        ## This will be the tick distance for the contrast axes.
        rawAxesTicks = fig.get_axes()[i-1].yaxis.get_majorticklocs()
        rawAxesTickDist = rawAxesTicks[1] - rawAxesTicks[0]

        ## First re-draw of axis with new tick interval
        fig.get_axes()[i].yaxis.set_major_locator(MultipleLocator(rawAxesTickDist))
        newticks1 = fig.get_axes()[i].get_yticks()

        if floatContrast is False:
            if (showAllYAxes is False and i in range( 2, len(fig.get_axes())) ):
                fig.get_axes()[i].get_yaxis().set_visible(showAllYAxes)
            # Set the contrast ylim if it is specified.
            # if contrastYlim is not None:
            #     fig.get_axes()[i].set_ylim(contrastYlim)
            #     lower = contrastYlim[0]
            #     upper = contrastYlim[1]
            else:
                ## Obtain major ticks that comfortably encompass lower and upper.
                newticks2 = list()
                for a,b in enumerate(newticks1):
                    if (b >= lower and b <= upper):
                        # if the tick lies within upper and lower, take it.
                        newticks2.append(b)
                # if the meandiff falls outside of the newticks2 set, add a tick in the right direction.
                if np.max(newticks2) < meandiff:
                    ind = np.where(newticks1 == np.max(newticks2))[0][0] # find out the max tick index in newticks1.
                    newticks2.append( newticks1[ind+1] )
                elif meandiff < np.min(newticks2):
                    ind = np.where(newticks1 == np.min(newticks2))[0][0] # find out the min tick index in newticks1.
                    newticks2.append( newticks1[ind-1] )
                newticks2 = np.array(newticks2)
                newticks2.sort()

                # newticks = list()
                # for a,b in enumerate(oldticks):
                #     if (b >= lower and b <= upper):
                #         newticks.append(b)
                # newticks = np.array(newticks)
                ## Re-draw the axis.
                fig.get_axes()[i].yaxis.set_major_locator(FixedLocator(locs = newticks2))
                #fig.get_axes()[i].yaxis.set_minor_locator(AutoMinorLocator(2))

                ## Draw minor ticks appropriately.
                #fig.get_axes()[i].yaxis.set_minor_locator(AutoMinorLocator(2))

                ## Draw zero reference line.
                fig.get_axes()[i].hlines(y = 0,
                    xmin = fig.get_axes()[i].get_xaxis().get_view_interval()[0], 
                    xmax = fig.get_axes()[i].get_xaxis().get_view_interval()[1],
                    linestyle = contrastZeroLineStyle,
                    linewidth = 0.75,
                    color = contrastZeroLineColor)

                sb.despine(ax = fig.get_axes()[i], trim = True, 
                    bottom = False, right = True,
                    left = False, top = True)

                ## Draw back the lines for the relevant y-axes.
                ymin = fig.get_axes()[i].get_yaxis().get_majorticklocs()[0]
                ymax = fig.get_axes()[i].get_yaxis().get_majorticklocs()[-1]
                x, _ = fig.get_axes()[i].get_xaxis().get_view_interval()
                fig.get_axes()[i].add_artist(Line2D((x, x), (ymin, ymax), color='black', linewidth=1))    

                ## Draw back the lines for the relevant x-axes.
                xmin = fig.get_axes()[i].get_xaxis().get_majorticklocs()[0]
                xmax = fig.get_axes()[i].get_xaxis().get_majorticklocs()[-1]
                y, _ = fig.get_axes()[i].get_yaxis().get_view_interval()
                fig.get_axes()[i].add_artist(Line2D((xmin, xmax), (y, y), color='black', linewidth=1.5)) 

        else:
            ## Get the original ticks on the floating y-axis.
            newticks1 = fig.get_axes()[i].get_yticks()

            ## Obtain major ticks that comfortably encompass lower and upper.
            newticks2 = list()
            for a,b in enumerate(newticks1):
                if (b >= lower and b <= upper):
                    # if the tick lies within upper and lower, take it.
                    newticks2.append(b)
            # if the meandiff falls outside of the newticks2 set, add a tick in the right direction.
            if np.max(newticks2) < meandiff:
                ind = np.where(newticks1 == np.max(newticks2))[0][0] # find out the max tick index in newticks1.
                newticks2.append( newticks1[ind+1] )
            elif meandiff < np.min(newticks2):
                ind = np.where(newticks1 == np.min(newticks2))[0][0] # find out the min tick index in newticks1.
                newticks2.append( newticks1[ind-1] )
            newticks2 = np.array(newticks2)
            newticks2.sort()

            # newticks = list()
            # for a,b in enumerate(oldticks):
            #     if (b >= lower and b <= upper):
            #         newticks.append(b)
            # newticks = np.array(newticks)

            ## Re-draw the axis.
            fig.get_axes()[i].yaxis.set_major_locator(FixedLocator(locs = newticks2))
            #fig.get_axes()[i].yaxis.set_minor_locator(AutoMinorLocator(2))
            
            ## Obtain minor ticks that fall within the major ticks.
            # majorticks = fig.get_axes()[i].yaxis.get_majorticklocs()
            # oldminorticks = fig.get_axes()[i].yaxis.get_minorticklocs()
            # newminorticks = list()
            # for a,b in enumerate(oldminorticks):
            #     if (b >= majorticks[0] and b <= majorticks[-1]):
            #         newminorticks.append(b)
            # newminorticks = np.array(newminorticks)
            # fig.get_axes()[i].yaxis.set_minor_locator(FixedLocator(locs = newminorticks))    

            ## Despine and trim the axes.
            sb.despine(ax = fig.get_axes()[i], trim = True, 
                bottom = False, right = False,
                left = True, top = True)

    for i in range(0, len(fig.get_axes()), 2):
        # Loop through the raw data swarmplots and despine them appropriately.
        if floatContrast is True:
            sb.despine(ax = fig.get_axes()[i], trim = True, right = True)

        else:
            sb.despine(ax = fig.get_axes()[i], trim = True, bottom = True, right = True)
            fig.get_axes()[i].get_xaxis().set_visible(False)

        # Draw back the lines for the relevant y-axes.
        ymin = fig.get_axes()[i].get_yaxis().get_majorticklocs()[0]
        ymax = fig.get_axes()[i].get_yaxis().get_majorticklocs()[-1]
        x, _ = fig.get_axes()[i].get_xaxis().get_view_interval()
        fig.get_axes()[i].add_artist(Line2D((x, x), (ymin, ymax), color='black', linewidth=1.5))    

    # Zero gaps between plots on the same row, if floatContrast is False
    if (floatContrast is False and showAllYAxes is False):
        gsMain.update(wspace = 0)
    else:    
        # Tight Layout!
        gsMain.tight_layout(fig)

    # And we're done.
    rcdefaults() # restore matplotlib defaults.
    sb.set() # restore seaborn defaults.
    return fig, contrastList