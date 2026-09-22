from unittest.mock import MagicMock

import pytest
from matplotlib.colors import Colormap
from napari.utils.colormaps import ALL_COLORMAPS
from qtpy.QtCore import QEvent, QPoint
from qtpy.QtGui import QHelpEvent
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStyleOptionViewItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from napari_relax._util_classes import (
    BigDatasetNamesDialog,
    Containerize,
    DelayedTooltipEventFilter,
    LayerCorrectorTreeProducer,
    LoadingDialog,
    QtViewerWrap,
    SetupDialog,
    TabTemplate,
    TimeResDialog,
    TooltipButton,
)
from napari_relax._util_classes.custom_colorboxes import (
    ColorBoxLabel,
    MplCompatibleColorCombobox,
)
from napari_relax._util_classes.custom_colorboxes.mpl_compatible_combobox import (  # noqa: E501
    QUANTITATIVE_CMAPS,
    CustomColorStyledDelegate,
    CustomQtColormapComboBox,
    make_image,
)

from .conftest import LINEAGE_A, add_lt_layer, points_of


class TestContainerize:
    def test_horizontal(self, qtbot):
        labels = [QLabel("a"), QLabel("b")]
        container = Containerize(labels)
        qtbot.addWidget(container)
        assert isinstance(container.layout(), QHBoxLayout)
        assert container.layout().count() == 2
        assert labels[0].parent() is container

    def test_vertical(self, qtbot):
        container = Containerize([QLabel("a")], horizontal=False)
        qtbot.addWidget(container)
        assert isinstance(container.layout(), QVBoxLayout)


def test_tooltip_button(qtbot):
    button = TooltipButton("<b>help</b>")
    qtbot.addWidget(button)
    assert button.text() == "?"
    assert button.toolTip() == "<b>help</b>"
    assert (button.width(), button.height()) == (30, 30)
    assert not button.isCheckable()


class TestDelayedTooltipEventFilter:
    @pytest.fixture
    def widget(self, qtbot):
        widget = QWidget()
        widget.setToolTip("delayed")
        qtbot.addWidget(widget)
        return widget

    @staticmethod
    def tooltip_event():
        return QHelpEvent(QEvent.ToolTip, QPoint(1, 2), QPoint(3, 4))

    def test_tooltip_event_starts_the_timer(self, widget):
        event_filter = DelayedTooltipEventFilter()
        assert event_filter.eventFilter(widget, self.tooltip_event())
        assert event_filter.timer.isActive()
        assert event_filter.tooltip_text == "delayed"
        assert event_filter.widget is widget
        assert event_filter.pos == QPoint(3, 4)

    def test_leave_event_cancels(self, widget, monkeypatch):
        hidden = []
        monkeypatch.setattr(QToolTip, "hideText", lambda: hidden.append(1))
        event_filter = DelayedTooltipEventFilter()
        event_filter.eventFilter(widget, self.tooltip_event())
        event_filter.eventFilter(widget, QEvent(QEvent.Leave))
        assert not event_filter.timer.isActive()
        assert event_filter.tooltip_text == ""
        assert event_filter.widget is None
        assert hidden

    def test_other_events_are_not_filtered(self, widget):
        assert not DelayedTooltipEventFilter().eventFilter(
            widget, QEvent(QEvent.Enter)
        )

    def test_tooltip_is_shown_after_the_delay(
        self, qtbot, widget, monkeypatch
    ):
        shown = []
        monkeypatch.setattr(
            QToolTip, "showText", lambda *args: shown.append(args)
        )
        event_filter = DelayedTooltipEventFilter()
        event_filter.delay = 10
        event_filter.eventFilter(widget, self.tooltip_event())
        qtbot.waitUntil(lambda: bool(shown), timeout=1000)
        assert shown == [(QPoint(3, 4), "delayed", widget)]

    def test_empty_tooltip_is_not_shown(self, monkeypatch):
        shown = []
        monkeypatch.setattr(
            QToolTip, "showText", lambda *args: shown.append(args)
        )
        DelayedTooltipEventFilter().show_tooltip()
        assert not shown


class TestDialogs:
    def test_loading_dialog(self, qtbot):
        dialog = LoadingDialog(["A loader", "B loader"])
        qtbot.addWidget(dialog)
        assert sorted(dialog.match.values()) == ["A loader", "B loader"]
        assert dialog.value_selected == ""
        checkbox = next(c for c, o in dialog.match.items() if o == "B loader")
        checkbox.setChecked(True)
        assert dialog.value_selected == "B loader"
        assert dialog.result() == LoadingDialog.Accepted

    @pytest.mark.parametrize(
        ("button", "expected"), [("yes", True), ("no", False)]
    )
    def test_big_dataset_names_dialog(self, qtbot, button, expected):
        dialog = BigDatasetNamesDialog()
        qtbot.addWidget(dialog)
        getattr(dialog, f"{button}_but").pressed.emit()
        assert dialog.continue_proccess is expected
        assert dialog.result() == BigDatasetNamesDialog.Accepted

    def test_time_resolution_dialog_defaults(self, qtbot):
        dialog = TimeResDialog()
        qtbot.addWidget(dialog)
        assert dialog.tr_edit.value == "0"
        assert dialog.value_selected == 0
        dialog = TimeResDialog(current=2.5)
        qtbot.addWidget(dialog)
        assert dialog.tr_edit.value == "2.5"

    def test_time_resolution_dialog_ok(self, qtbot):
        dialog = TimeResDialog(current=1)
        qtbot.addWidget(dialog)
        dialog.tr_edit.value = "7.5"
        dialog.ok_but.native.click()
        assert dialog.value_selected == 7.5
        assert dialog.result() == TimeResDialog.Accepted

    def test_time_resolution_dialog_invalid_value(self, qtbot):
        dialog = TimeResDialog(current=1)
        qtbot.addWidget(dialog)
        dialog.tr_edit.value = "fast"
        dialog.ok_but.native.click()
        assert dialog.value_selected == 0
        assert dialog.result() != TimeResDialog.Accepted

    def test_setup_dialog_parameters(self, qtbot, lt):
        dialog = SetupDialog(lt, current=lt.time_resolution)
        qtbot.addWidget(dialog)
        assert dialog.tr_edit.value == "5.0"
        dialog.slider.setValue(12)
        assert dialog.value_shown.text() == "12"
        dialog.rescaler.setChecked(True)
        dialog.check_resave.setChecked(True)
        dialog.ok_but.native.click()
        assert dialog.parameters == {
            "divisor": 12,
            "time_r": 5.0,
            "rescale": True,
            "resave": True,
        }

    def test_setup_dialog_invalid_value(self, qtbot, lt):
        dialog = SetupDialog(lt)
        qtbot.addWidget(dialog)
        dialog.tr_edit.value = "?"
        dialog._ok_pressed(None)
        assert not hasattr(dialog, "parameters")

    def test_setup_dialog_cancel(self, qtbot, lt):
        dialog = SetupDialog(lt)
        qtbot.addWidget(dialog)
        dialog._cancel_pressed()
        assert dialog.parameters == {}
        assert dialog.result() == SetupDialog.Accepted


class TestTabTemplate:
    @pytest.fixture
    def tab(self, qtbot, lt):
        tab = TabTemplate(lt, "embryo")
        qtbot.addWidget(tab)
        return tab

    def test_roots_are_the_labelled_nodes(self, tab):
        assert [root for root, _ in tab.roots] == [1, 10, 20]
        assert tab.roots[2][1] == "C - 20 starts from 2 timepoint"
        assert tab.root_list.count() == 3

    def test_label_inside_a_chain_uses_the_chain_start(self, qtbot, lt):
        lt.labels.clear()
        lt.labels[2] = "middle"
        tab = TabTemplate(lt, "embryo")
        qtbot.addWidget(tab)
        assert tab.roots == [(1, "middle - 1 starts from 0 timepoint")]

    def test_show_roots(self, tab):
        assert tab.show_roots() == []
        tab.root_list.item(0).setSelected(True)
        tab.root_list.item(2).setSelected(True)
        assert tab.show_roots() == [1, 20]

    def test_times_from_range(self, tab):
        tab.times_slicer.value = slice(2, 11, 3)
        tab.times_selector()
        assert tab.times == [2, 5, 8]
        assert tab.ret_times() == [2, 5, 8]

    def test_times_single_value(self, tab):
        tab.times_slicer.value = slice(4, 4, 1)
        assert tab.ret_times() == [4]

    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="BUG: the list of times is read from `self.time_list` but "
        "the widget is stored as `self.times_list`",
    )
    def test_times_from_list(self, tab):
        tab.times_list_check.setChecked(True)
        tab.times_list.setText("7, 3,3")
        assert tab.ret_times() == [3, 7]

    def test_time_cropping(self, tab):
        tab.time_cropper.setText("4")
        tab.time_cropper.returnPressed.emit()
        assert tab.crop == 4
        assert tab.time_cropper.placeholderText() == "Final Timepoint: 4"
        assert tab.time_cropper.text() == ""
        tab.time_cropper.returnPressed.emit()
        assert tab.crop is None

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: time_cropping stores the crop in `crop`, but the "
        "cross comparison reads `time_crop`, which stays None",
    )
    def test_time_cropping_updates_time_crop(self, tab):
        tab.time_cropper.setText("4")
        tab.time_cropper.returnPressed.emit()
        assert tab.time_crop == 4


def test_qt_viewer_wrap_forwards_dropped_files():
    main_viewer = MagicMock()
    fake_wrap = MagicMock(main_viewer=main_viewer)
    QtViewerWrap._qt_open(fake_wrap, ["a.lT"], False, "napari-relax", None)
    main_viewer.window._qt_viewer._qt_open.assert_called_once_with(
        ["a.lT"], False, "napari-relax", None
    )


class TestColorBoxLabel:
    def test_colormaps(self, qtbot):
        box = ColorBoxLabel(None)
        qtbot.addWidget(box)
        combobox = box.combobox_continuous
        assert combobox.count() == len(ALL_COLORMAPS)
        combobox.setCurrentIndex(combobox.findData("magma"))
        assert box.get_cmap() is ALL_COLORMAPS["magma"]
        assert box.value() == combobox.currentText()
        assert not box.color_label.icon().isNull()


class TestMplCompatibleColorCombobox:
    def test_default_colormaps(self, qtbot):
        box = MplCompatibleColorCombobox()
        qtbot.addWidget(box)
        assert box.dict_of_cmaps is QUANTITATIVE_CMAPS
        assert box.combobox_continuous.count() == len(QUANTITATIVE_CMAPS)
        assert box.get_cmap() is QUANTITATIVE_CMAPS["Pastel1"]
        assert not box.color_label.icon().isNull()

    def test_custom_colormaps(self, qtbot):
        from matplotlib import colormaps

        cmaps = {name: colormaps[name] for name in ("viridis", "Reds")}
        box = MplCompatibleColorCombobox(None, cmaps)
        qtbot.addWidget(box)
        box.combobox_continuous.setCurrentIndex(1)
        assert box.get_cmap() is cmaps["Reds"]
        assert isinstance(box.get_cmap(), Colormap)

    def test_make_image(self):
        cmap = QUANTITATIVE_CMAPS["tab10"]
        image = make_image(cmap, width=32, height=4)
        assert (image.width(), image.height()) == (32, 4)
        first, last = image.pixelColor(0, 0), image.pixelColor(31, 3)
        assert first.getRgbF()[:3] == pytest.approx(cmap(0.0)[:3], abs=0.01)
        assert last.getRgbF()[:3] == pytest.approx(cmap(1.0)[:3], abs=0.01)

    def test_delegate_size_and_paint(self, qtbot):
        combobox = CustomQtColormapComboBox()
        qtbot.addWidget(combobox)
        combobox.addItem("tab10", "tab10")
        combobox.addItem("unknown", "unknown")
        delegate = combobox.view().itemDelegate()
        assert isinstance(delegate, CustomColorStyledDelegate)
        index = combobox.model().index(0, 0)
        size = delegate.sizeHint(QStyleOptionViewItem(), index)
        assert size.height() == 24
        from qtpy.QtGui import QImage, QPainter

        image = QImage(400, 30, QImage.Format_RGBA8888)
        painter = QPainter(image)
        option = QStyleOptionViewItem()
        option.rect = image.rect()
        delegate.paint(painter, option, index)
        delegate.paint(painter, option, combobox.model().index(1, 0))
        painter.end()


class TestLayerCorrectorTreeProducer:
    @pytest.fixture
    def producer(self, qtbot, viewer):
        producer = LayerCorrectorTreeProducer(viewer)
        qtbot.addWidget(producer)
        return producer

    def test_get_lt(self, producer, viewer, lt):
        assert producer.get_lT() is None
        layer = add_lt_layer(viewer, lt)
        viewer.layers.selection.active = layer
        assert producer.get_lT() is lt

    def test_sub_points_selector(self, producer, lt_layer):
        lt_layer.selected_data = set(points_of(lt_layer, [3]))
        producer.sub_points_selector()
        assert lt_layer.selected_data == set(
            points_of(lt_layer, [3, 4, 5, 6, 7, 8, 9])
        )

    def test_sub_points_selector_without_selection(self, producer, lt_layer):
        assert producer.sub_points_selector() == 0

    @pytest.mark.parametrize("node", sorted(LINEAGE_A) + [10, 15])
    def test_val_finder(self, producer, lt_layer, lt, node):
        graphs = lt_layer.metadata["graphs"][0]
        index = producer.val_finder(node, lt, graphs)
        assert graphs[index]["root"] == (1 if node in LINEAGE_A else 10)

    @pytest.mark.xfail(
        strict=True,
        reason="BUG: get_ancestor_at_t(node) returns -1 when the root "
        "starts after the first timepoint, so late lineages are not found",
    )
    def test_val_finder_late_root(self, producer, lt_layer, lt):
        graphs = lt_layer.metadata["graphs"][0]
        index = producer.val_finder(24, lt, graphs)
        assert index is not None and graphs[index]["root"] == 20
