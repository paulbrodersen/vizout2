import warnings
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from matplotlib.patches import Ellipse
from matplotlib.transforms import Affine2D


class ClickableArtists:
    """Implements selection of matplotlib artists via the mouse left click (+/- ctrl or command key).

    Notes
    -----
    Adapted from: https://stackoverflow.com/a/47312637/2912349

    """
    def __init__(self, artists):

        try:
            self.fig, = set(list(artist.figure for artist in artists))
        except ValueError:
            raise Exception("All artists have to be on the same figure!")

        try:
            self.ax, = set(list(artist.axes for artist in artists))
        except ValueError:
            raise Exception("All artists have to be on the same axis!")

        self.fig.canvas.mpl_connect('button_release_event', self._on_release)

        self._clickable_artists = list(artists)
        self._selected_artists = []
        self._base_linewidth = dict([(artist, artist.get_linewidth()) for artist in artists])
        self._base_edgecolor = dict([(artist, artist.get_edgecolor()) for artist in artists])

        if plt.get_backend() == 'MacOSX':
            msg  = "You appear to be using the MacOSX backend."
            msg += "\nModifier key presses are bugged on this backend. See https://github.com/matplotlib/matplotlib/issues/20486"
            msg += "\nConsider using a different backend, e.g. TkAgg (import matplotlib; matplotlib.use('TkAgg'))."
            msg += "\nNote that you must set the backend before importing any package depending on matplotlib."
            warnings.warn(msg)


    def _on_release(self, event):
        if event.inaxes == self.ax:
            for artist in self._clickable_artists:
                if artist.contains(event)[0]:
                    if event.key in ('control', 'super+??', 'ctrl+??'):
                        self._toggle_select_artist(artist)
                    else:
                        self._deselect_all_other_artists(artist)
                        self._toggle_select_artist(artist)
                        # NOTE: if two artists are overlapping, only the first one encountered is selected!
                    break
            else:
                if not event.key in ('control', 'super+??', 'ctrl+??'):
                    self._deselect_all_artists()
        else:
            # warnings.warn("Clicked outside of axis!")
            pass


    def _toggle_select_artist(self, artist):
        if artist in self._selected_artists:
            self._deselect_artist(artist)
        else:
            self._select_artist(artist)


    def _select_artist(self, artist):
        if not (artist in self._selected_artists):
            linewidth = self._base_linewidth[artist]
            artist.set_linewidth(1.5 * linewidth)
            artist.set_edgecolor('black')
            self._selected_artists.append(artist)
            self.fig.canvas.draw_idle()


    def _deselect_artist(self, artist):
        if artist in self._selected_artists:
            artist.set_linewidth(self._base_linewidth[artist])
            artist.set_edgecolor(self._base_edgecolor[artist])
            self._selected_artists.remove(artist)
            self.fig.canvas.draw_idle()


    def _deselect_all_artists(self):
        for artist in self._selected_artists[:]: # copy the list with [:], as we are modifying the list being iterated over
            self._deselect_artist(artist)


    def _deselect_all_other_artists(self, artist_to_keep):
        for artist in self._selected_artists[:]:
            if artist != artist_to_keep:
                self._deselect_artist(artist)


class SelectableArtists(ClickableArtists):
    """Augments :py:class:`ClickableArtists` with a rectangle selector.

    Notes
    -----
    Adapted from: https://stackoverflow.com/a/47312637/2912349

    """
    def __init__(self, artists):
        super().__init__(artists)

        self.fig.canvas.mpl_connect('button_press_event', self._on_press)
        self.fig.canvas.mpl_connect('motion_notify_event',  self._on_motion)

        self._selectable_artists = list(artists)
        self._currently_selecting = False

        self._rect = plt.Rectangle((0, 0), 1, 1, linestyle="--", edgecolor="crimson", fill=False)
        self.ax.add_patch(self._rect)
        self._rect.set_visible(False)

        self._x0 = 0
        self._y0 = 0
        self._x1 = 0
        self._y1 = 0


    def _on_press(self, event):

        if event.inaxes == self.ax:
            # reset rectangle
            self._x0 = event.xdata
            self._y0 = event.ydata
            self._x1 = event.xdata
            self._y1 = event.ydata

            for artist in self._clickable_artists:
                if artist.contains(event)[0]:
                    break
            else:
                self._currently_selecting = True


    def _on_release(self, event):
        super()._on_release(event)

        if self._currently_selecting:
            # select artists inside window
            for artist in self._selectable_artists:
                if self._is_inside_rect(*artist.center):
                    if event.key in ('control', 'super+??', 'ctrl+??'): # if/else probably superfluouos
                        self._toggle_select_artist(artist)              # as no artists will be selected
                    else:                                               # if control is not held previously
                        self._select_artist(artist)                     #

            # stop window selection and draw new state
            self._currently_selecting = False
            self._rect.set_visible(False)
            self.fig.canvas.draw_idle()


    def _on_motion(self, event):
        if event.inaxes == self.ax:
            if self._currently_selecting:
                self._x1 = event.xdata
                self._y1 = event.ydata
                # add rectangle for selection here
                self._selector_on()


    def _is_inside_rect(self, x, y):
        xlim = np.sort([self._x0, self._x1])
        ylim = np.sort([self._y0, self._y1])
        if (xlim[0]<=x) and (x<xlim[1]) and (ylim[0]<=y) and (y<ylim[1]):
            return True
        else:
            return False


    def _selector_on(self):
        self._rect.set_visible(True)
        xlim = np.sort([self._x0, self._x1])
        ylim = np.sort([self._y0, self._y1])
        self._rect.set_xy((xlim[0], ylim[0]))
        self._rect.set_width(xlim[1] - xlim[0])
        self._rect.set_height(ylim[1] - ylim[0])
        self.fig.canvas.draw_idle()


class SelectableAnnotatedArtists(SelectableArtists):
    """Augments :py:class:`SelectableArtists`.
    Upon selection, an artist label is displayed.

    """
    def __init__(self, artists, xy, labels, **kwargs):
        super().__init__(artists)
        text_objects = list(self._annotate(xy, labels, **kwargs))
        self._artist_to_label = dict(zip(artists, labels))
        self._artist_to_text_object = dict(zip(artists, text_objects))


    def _annotate(self, xy, labels, **kwargs):
        for point, label in zip(xy, labels):
            yield self.ax.annotate(label, point, visible=False, **kwargs)


    def _select_artist(self, artist):
        super()._select_artist(artist)
        self._artist_to_text_object[artist].set_visible(True)


    def _deselect_artist(self, artist):
        super()._deselect_artist(artist)
        self._artist_to_text_object[artist].set_visible(False)


class SelectableArtistGroups(SelectableAnnotatedArtists):
    """Augments :py:class:`SelectableAnnotatedArtists` with cross-subplot peer linking.

    When an artist is selected or deselected, all artists representing the same
    data row in other subplots are selected or deselected accordingly.
    The peer registry (``artist_to_peers``) is populated externally after all
    subplots have been created, e.g. by :py:class:`OutlierSelector`.

    """
    def __init__(self, artists, xy, labels, **kwargs):
        super().__init__(artists, xy, labels, **kwargs)
        # Maps each local artist to a list of (group, artist) pairs in other subplots.
        # Populated externally by OutlierSelector after all subplots are created.
        self._artist_to_peers = {artist: [] for artist in artists}


    def _select_artist(self, artist):
        if artist in self._selected_artists:
            return
        super()._select_artist(artist)
        for peer_group, peer_artist in self._artist_to_peers[artist]:
            peer_group._select_artist(peer_artist)


    def _deselect_artist(self, artist):
        if artist not in self._selected_artists:
            return
        super()._deselect_artist(artist)
        for peer_group, peer_artist in self._artist_to_peers[artist]:
            peer_group._deselect_artist(peer_artist)


class OutlierSelector:

    def __init__(self, data, markersize=0.05, n_std=2, **kwargs):

        total_points, total_columns = data.shape
        figure, axes = plt.subplots(
            total_columns, total_columns,
            sharex="col", sharey="row",
            subplot_kw=dict(aspect="equal"),
            figsize=(10, 10), # maximum square figure dimensions in matplotlib
        )

        self._artist_groups = list(self._draw(data, axes, markersize, **kwargs))
        self._draw_standard_deviations(data, axes, n_std)
        self._label_axes(data, axes)
        self._link_peers(data)
        figure.tight_layout()
        plt.show()


    def _draw(self, data, axes, markersize, **kwargs):
        for ii, x in enumerate(data.columns):
            for jj, y in enumerate(data.columns):
                artists = self._scatter(data[[x, y]].values, axes[ii, jj], markersize, **kwargs)
                yield SelectableArtistGroups(
                    artists, data[[x, y]].values, list(data.index),
                    xytext=(3, 2), textcoords="offset points")


    def _scatter(self, xy, ax, markersize, **kwargs):
        """Re-implement scatter, but each dot is an individual artist."""

        artists = []
        for point in xy:
            artist = plt.Circle(point, markersize, **kwargs)
            ax.add_patch(artist)
            artists.append(artist)

        ax.relim()
        ax.autoscale_view()

        return artists


    def _draw_standard_deviations(self, data, axes, n_std):
        for ii, x in enumerate(data.columns):
            for jj, y in enumerate(data.columns):
                if ii > jj:
                    confidence_ellipse(
                        data[x], data[y], axes[ii, jj], n_std=n_std,
                        edgecolor="red", linewidth=1)


    def _label_axes(self, data, axes):
        for ax, label in zip(axes[:, 0], data.columns):
            ax.set_ylabel(label)
        for ax, label in zip(axes[0, :], data.columns):
            ax.set_title(label)


    def _link_peers(self, data):
        """For every data-row index, collect the corresponding artist from each
        subplot and register all of them as peers of one another."""
        n_rows = len(data)
        for row_idx in range(n_rows):
            # Build a list of (group, artist) pairs for this data row across all subplots
            row_peers = [
                (group, group._selectable_artists[row_idx])
                for group in self._artist_groups
            ]
            # Tell each group about the peers that live in *other* subplots
            for group in self._artist_groups:
                local_artist = group._selectable_artists[row_idx]
                group._artist_to_peers[local_artist] = [
                    (peer_group, peer_artist)
                    for peer_group, peer_artist in row_peers
                    if peer_group is not group
                ]


    def get_outliers(self):
        artists = self._artist_groups[0]
        return [artists._artist_to_label[artist] for artist in artists._selected_artists]


def confidence_ellipse(x, y, ax, n_std=3.0, facecolor='none', **kwargs):
    """
    Create a plot of the covariance confidence ellipse of *x* and *y*.

    Parameters
    ----------
    x, y : array-like, shape (n, )
        Input data.

    ax : matplotlib.axes.Axes
        The Axes object to draw the ellipse into.

    n_std : float
        The number of standard deviations to determine the ellipse's radiuses.

    **kwargs
        Forwarded to `~matplotlib.patches.Ellipse`

    Returns
    -------
    matplotlib.patches.Ellipse

    Notes
    -----
    From: https://matplotlib.org/stable/gallery/statistics/confidence_ellipse.html

    """
    if x.size != y.size:
        raise ValueError("x and y must be the same size")

    cov = np.cov(x, y)
    pearson = cov[0, 1]/np.sqrt(cov[0, 0] * cov[1, 1])
    # Using a special case to obtain the eigenvalues of this
    # two-dimensional dataset.
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2,
                          facecolor=facecolor, **kwargs)

    # Calculating the standard deviation of x from
    # the squareroot of the variance and multiplying
    # with the given number of standard deviations.
    scale_x = np.sqrt(cov[0, 0]) * n_std
    mean_x = np.mean(x)

    # calculating the standard deviation of y ...
    scale_y = np.sqrt(cov[1, 1]) * n_std
    mean_y = np.mean(y)

    transf = Affine2D() \
        .rotate_deg(45) \
        .scale(scale_x, scale_y) \
        .translate(mean_x, mean_y)

    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)


if __name__ == "__main__":

    n = 100
    df = pd.DataFrame(dict({char : np.random.randn(n) for char in "abc"}))
    p = OutlierSelector(df)
    print(p.get_outliers())
