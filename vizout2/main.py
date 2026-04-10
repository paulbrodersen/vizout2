import warnings
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


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
        self.artist_to_label = dict(zip(artists, text_objects))


    def _annotate(self, xy, labels, **kwargs):
        for point, label in zip(xy, labels):
            yield self.ax.annotate(label, point, visible=False, **kwargs)


    def _select_artist(self, artist):
        super()._select_artist(artist)
        self.artist_to_label[artist].set_visible(True)


    def _deselect_artist(self, artist):
        super()._deselect_artist(artist)
        self.artist_to_label[artist].set_visible(False)


class OutlierSelector:

    def __init__(self, data, markersize=2, **kwargs):

        total_points, total_columns = data.shape
        figure, axes = plt.subplots(
            total_columns, total_columns,
            sharex="col", sharey="row",
            subplot_kw=dict(aspect="equal"),
            figsize=(10, 10), # maximum square figure dimensions in matplotlib
        )

        self.artist_groups = list(self._draw(data, axes, markersize, **kwargs))
        self._label_axes(data, axes)
        figure.tight_layout()
        plt.show()


    def _draw(self, data, axes, markersize, **kwargs):
        for ii, x in enumerate(data.columns):
            for jj, y in enumerate(data.columns):
                artists = list(self._scatter(data[[x, y]].values, axes[ii, jj], markersize, **kwargs))
                yield(SelectableAnnotatedArtists(
                    artists, data[[x, y]].values, list(data.index), xytext=(7.5, 5), textcoords="offset points"))


    def _scatter(self, xy, ax, markersize, **kwargs):
        """Re-implement scatter, but each dot is an individual artist."""
        transform = ax.transData + ax.transAxes.inverted()
        xy_in_axis_coordinates = transform.transform(xy)
        radius = 0.01 * markersize # i.e. markersize is expressed as a percentage of the axis
        for point in xy_in_axis_coordinates:
            artist = plt.Circle(point, radius, transform=ax.transAxes, **kwargs)
            ax.add_patch(artist)
            yield(artist)


    def _label_axes(self, data, axes):
        for ax, label in zip(axes[:, 0], data.columns):
            ax.set_ylabel(label)
        for ax, label in zip(axes[-1, :], data.columns):
            ax.set_xlabel(label)


if __name__ == "__main__":

    # Random test data
    n = 100
    df = pd.DataFrame(dict({char : np.random.randn(n) for char in "abc"}))
    p = OutlierSelector(df)
