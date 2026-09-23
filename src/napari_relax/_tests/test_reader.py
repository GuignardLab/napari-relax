import uuid

import numpy as np
import pytest
from lineagetree import LineageTree

from napari_relax import _reader
from napari_relax._reader import (
    _extract_napari_surface_from_lT,
    graph_loading,
    initial_loading,
    layer_preparation,
    napari_get_reader,
    reader_function,
)
from napari_relax._util_classes import LoadingDialog, SetupDialog
from napari_relax._utils import _infer_point_size

from .conftest import (
    LINEAGE_A,
    LINEAGE_B,
    LINEAGE_C,
    POS,
    TIME,
    make_lineage_tree,
)


@pytest.fixture
def lt_file(tmp_path, lt):
    path = tmp_path / "my_embryo.lT"
    lt.write(str(path))
    return path


def press_ok(time_resolution=None, divisor=0, rescale=False, resave=False):
    """Make the Loading Parameters dialog return the given values."""

    def exec_(self):
        if time_resolution is not None:
            self.tr_edit.value = str(time_resolution)
        self.slider.setValue(divisor)
        self.rescaler.setChecked(rescale)
        self.check_resave.setChecked(resave)
        self._ok_pressed(None)

    return exec_


def press_cancel(self):
    self._cancel_pressed()


class TestNapariGetReader:
    @pytest.mark.parametrize(
        "path",
        [
            "embryo.lT",
            "embryo.lt",
            "embryo.LT",
            "dir.with.dots/embryo.lT",
            "tracks.xml",
            "tracks.mastodon",
            "tracks.bmf",
            "tracks.csv",
            "tracks.XML",
        ],
    )
    def test_supported(self, path):
        assert napari_get_reader(path) is reader_function

    @pytest.mark.parametrize("path", ["image.tif", "embryo", "data.npy"])
    def test_unsupported(self, path):
        assert napari_get_reader(path) is None

    def test_list_uses_first_path(self):
        assert napari_get_reader(["a.lT", "b.tif"]) is reader_function
        assert napari_get_reader(["b.tif", "a.lT"]) is None


class TestReaderFunction:
    def test_lt_file(self, monkeypatch, lt_file):
        monkeypatch.setattr(SetupDialog, "exec_", press_ok())
        layers = reader_function(str(lt_file))
        assert len(layers) == 1
        data, kwargs, layer_type = layers[0]
        assert layer_type == "points"
        assert data.shape == (len(TIME), 4)
        assert kwargs["name"] == "my_embryo"
        lT = kwargs["metadata"]["LineageTree"]
        assert isinstance(lT, LineageTree)
        assert set(lT.nodes) == set(TIME)

    def test_time_resolution_is_applied(self, monkeypatch, lt_file):
        monkeypatch.setattr(SetupDialog, "exec_", press_ok(2.5))
        (layer,) = reader_function(str(lt_file))
        assert layer[1]["metadata"]["LineageTree"].time_resolution == 2.5
        # Not resaved: the file keeps its original resolution.
        assert LineageTree.load(str(lt_file)).time_resolution == 5

    def test_resave(self, monkeypatch, lt_file):
        monkeypatch.setattr(SetupDialog, "exec_", press_ok(2.5, resave=True))
        reader_function(str(lt_file))
        assert LineageTree.load(str(lt_file)).time_resolution == 2.5

    def test_cancel_returns_none(self, monkeypatch, lt_file):
        monkeypatch.setattr(SetupDialog, "exec_", press_cancel)
        assert reader_function(str(lt_file)) is None

    def test_rescale_and_filter_are_forwarded(self, monkeypatch, lt_file):
        seen = {}

        def fake_preparation(lT, path, parameters):
            seen.update(parameters)
            return []

        monkeypatch.setattr(_reader, "layer_preparation", fake_preparation)
        monkeypatch.setattr(
            SetupDialog, "exec_", press_ok(divisor=4, rescale=True)
        )
        reader_function(str(lt_file))
        assert seen["divisor"] == 4
        assert seen["rescale"] is True

    def test_single_loader_is_used_without_asking(
        self, monkeypatch, tmp_path, lt
    ):
        calls = []

        def loader(path):
            calls.append(path)
            return lt

        def fail(*args, **kwargs):
            raise AssertionError("the loader selection should not open")

        monkeypatch.setattr(_reader, "LOADERS", {"fake": {"Only": loader}})
        monkeypatch.setattr(_reader, "LoadingDialog", fail)
        monkeypatch.setattr(SetupDialog, "exec_", press_ok())
        path = str(tmp_path / "tracks.fake")
        layers = reader_function(path)
        assert calls == [path]
        assert layers[0][1]["metadata"]["LineageTree"] is lt

    def test_selected_loader_is_used(self, monkeypatch, tmp_path, lt):
        used = []
        loaders = {
            "Loader A": lambda path: used.append("A") or lt,
            "Loader B": lambda path: used.append("B") or lt,
        }

        def choose_b(self):
            for checkbox, option in self.match.items():
                if option == "Loader B":
                    checkbox.setChecked(True)

        monkeypatch.setattr(_reader, "LOADERS", {"fake": loaders})
        monkeypatch.setattr(LoadingDialog, "exec_", choose_b)
        monkeypatch.setattr(SetupDialog, "exec_", press_ok())
        reader_function(str(tmp_path / "tracks.fake"))
        assert used == ["B"]

    def test_no_loader_selected_raises(self, monkeypatch, tmp_path, lt):
        loaders = {"Loader A": lambda p: lt, "Loader B": lambda p: lt}
        monkeypatch.setattr(_reader, "LOADERS", {"fake": loaders})
        with pytest.raises(Warning, match="select one reader"):
            reader_function(str(tmp_path / "tracks.fake"))

    def test_open_with_napari(self, monkeypatch, viewer, lt_file):
        monkeypatch.setattr(SetupDialog, "exec_", press_ok())
        layers = viewer.open(str(lt_file), plugin="napari-relax")
        (layer,) = layers
        assert layer.name == "my_embryo"
        assert "LineageTree" in layer.metadata
        assert len(layer.data) == len(TIME)


class TestInitialLoading:
    def test_positions_and_times(self, lt):
        loaded = initial_loading(lt)
        assert loaded.data.shape == (len(TIME), 5)
        reversed_pos = np.array([POS[n][::-1] for n in TIME], dtype=float)
        np.testing.assert_allclose(
            loaded.barycenter, reversed_pos.mean(axis=0)
        )
        for node, t in TIME.items():
            row = loaded.data[loaded.lT_to_here[node]]
            assert row[1] == t
            np.testing.assert_allclose(
                row[2:], np.array(POS[node][::-1]) - loaded.barycenter
            )
        np.testing.assert_allclose(
            loaded.data[:, 2:].mean(axis=0), 0, atol=1e-12
        )

    def test_mappings_are_inverse(self, lt):
        loaded = initial_loading(lt)
        assert set(loaded.lT_to_here) == set(TIME)
        assert sorted(loaded.here_to_lT) == list(range(len(TIME)))
        for node, index in loaded.lT_to_here.items():
            assert loaded.here_to_lT[index] == node

    def test_tracks_follow_the_chains(self, lt):
        loaded = initial_loading(lt)
        for i, chain in enumerate(lt.all_chains):
            assert loaded.first_c_to_track[chain[0]] == i
            assert loaded.last_c_of_track[i] == chain[-1]
            track_ids = {loaded.data[loaded.lT_to_here[n], 0] for n in chain}
            assert track_ids == {i}

    def test_one_clone_and_color_per_lineage(self, lt):
        loaded = initial_loading(lt)

        def clones(nodes):
            return {loaded.clone[loaded.lT_to_here[n]] for n in nodes}

        clone_ids = [clones(lineage) for lineage in (LINEAGE_A, LINEAGE_B)]
        clone_ids.append(clones(LINEAGE_C))
        assert all(len(ids) == 1 for ids in clone_ids)
        assert set.union(*clone_ids) == {1, 2, 3}
        for index, clone in enumerate(loaded.clone):
            np.testing.assert_allclose(
                loaded.default_colors[index],
                np.ravel(loaded.cmap.map(clone)),
            )

    def test_no_scaling(self, lt):
        loaded = initial_loading(lt, scaling=False)
        assert loaded.rescaling_factor == 1
        assert lt.spatial_resolution == 1

    def test_scaling_divides_by_the_longest_distance(self, lt):
        unscaled = initial_loading(lt).data
        loaded = initial_loading(lt, scaling=True)
        assert loaded.rescaling_factor == pytest.approx(50)
        np.testing.assert_allclose(loaded.data[:, 2:], unscaled[:, 2:] / 50)
        np.testing.assert_allclose(loaded.data[:, :2], unscaled[:, :2])
        assert lt.spatial_resolution == pytest.approx(1 / 50)


class TestGraphLoading:
    def test_one_graph_per_root(self, lt):
        loaded = initial_loading(lt)
        graphs, pos, _ = graph_loading(
            lt, loaded.last_c_of_track, loaded.first_c_to_track, 0
        )
        assert {g["root"] for g in graphs.values()} == {1, 10, 20}
        assert set(pos) == set(graphs)
        for i, graph in graphs.items():
            root = graph["root"]
            # The root is drawn at minus its timepoint.
            assert pos[i][root][1] == -lt.time[root]
            assert set(graph["links"]) <= set(pos[i])

    def test_chain_connectivity(self, lt):
        loaded = initial_loading(lt)
        _, _, graph = graph_loading(
            lt, loaded.last_c_of_track, loaded.first_c_to_track, 0
        )
        track = loaded.first_c_to_track
        assert graph[track[4]] == [track[1]]
        assert graph[track[5]] == [track[1]]
        assert graph[track[22]] == [track[20]]
        assert graph[track[23]] == [track[20]]
        assert track[10] not in graph

    def test_divisor_filters_short_lineages(self):
        # A 20 timepoint chain and a 2 node lineage: with a divisor of 2,
        # lineages need at least 19 / 2 nodes.
        successor = {i: [i + 1] for i in range(19)} | {19: []}
        successor |= {100: [101], 101: []}
        time = {i: i for i in range(20)} | {100: 0, 101: 1}
        lT = LineageTree(successor=successor, time=time, starting_time=None)
        chains = {c[0]: i for i, c in enumerate(lT.all_chains)}
        last = {i: c[-1] for i, c in enumerate(lT.all_chains)}
        graphs, _, _ = graph_loading(lT, last, chains, 2)
        assert [g["root"] for g in graphs.values()] == [0]
        graphs, _, _ = graph_loading(lT, last, chains, 0)
        assert sorted(g["root"] for g in graphs.values()) == [0, 100]


class TestLayerPreparation:
    def test_points_layer(self, lt):
        layers = layer_preparation(lt, "embryo", parameters={})
        assert len(layers) == 1
        data, kwargs, layer_type = layers[0]
        loaded = initial_loading(make_lineage_tree())
        assert layer_type == "points"
        np.testing.assert_allclose(data, loaded.data[:, 1:])
        assert kwargs["name"] == "embryo"
        assert kwargs["shading"] == "spherical"
        np.testing.assert_allclose(kwargs["face_color"], loaded.default_colors)
        np.testing.assert_array_equal(
            kwargs["properties"]["clone"], loaded.clone
        )
        assert not kwargs["properties"]["Selection"].any()

    def test_metadata(self, lt):
        (_, kwargs, _) = layer_preparation(lt, "embryo", parameters={})[0]
        metadata = kwargs["metadata"]
        assert metadata["LineageTree"] is lt
        assert metadata["name_for_manager"] == "embryo"
        uuid.UUID(metadata["lineage_tree_id"])
        graphs, pos = metadata["graphs"]
        assert {g["root"] for g in graphs.values()} == {1, 10, 20}
        assert set(pos) == set(graphs)
        tracks = metadata["graph_to_create_tracks"]
        assert set(tracks["properties"]) == {"Lineage", "Selection"}
        assert metadata["data"].shape == (len(TIME), 5)
        for node, index in metadata["lT2napari"].items():
            assert metadata["napari2lT"][index] == node

    def test_point_size(self, lt):
        (_, kwargs, _) = layer_preparation(lt, "embryo", parameters={})[0]
        bounds = _infer_point_size(make_lineage_tree())
        assert kwargs["metadata"]["size_display_bounds"] == pytest.approx(
            bounds
        )
        assert kwargs["size"] == pytest.approx(bounds[1])

    def test_existing_file_gives_its_stem(self, lt, lt_file):
        (_, kwargs, _) = layer_preparation(lt, str(lt_file), parameters={})[0]
        assert kwargs["name"] == "my_embryo"
        assert kwargs["metadata"]["name_for_manager"] == "my_embryo"

    def test_other_names_are_kept(self, lt, tmp_path):
        name = str(tmp_path / "missing.lT")
        (_, kwargs, _) = layer_preparation(lt, name, parameters={})[0]
        assert kwargs["name"] == name

    def test_no_graph(self, lt):
        (_, kwargs, _) = layer_preparation(
            lt, "embryo", no_graph=True, parameters={}
        )[0]
        assert kwargs["metadata"]["graphs"] == ((), ())
        assert kwargs["metadata"]["graph_to_create_tracks"]["graph"] == ()

    def test_divisor(self, lt, monkeypatch):
        seen = []
        original = _reader.graph_loading

        def spy(lT, last, first, divisor):
            seen.append(divisor)
            return original(lT, last, first, divisor)

        monkeypatch.setattr(_reader, "graph_loading", spy)
        layer_preparation(lt, "embryo", parameters={"divisor": 3})
        assert seen == [3]

    def test_rescale(self, lt):
        (data, _, _) = layer_preparation(
            lt, "embryo", parameters={"rescale": True}
        )[0]
        unscaled = initial_loading(make_lineage_tree()).data[:, 2:]
        np.testing.assert_allclose(data[:, 1:], unscaled / 50)

    def test_unique_identifier_per_call(self, lt):
        ids = {
            layer_preparation(lt, "embryo", parameters={})[0][1]["metadata"][
                "lineage_tree_id"
            ]
            for _ in range(3)
        }
        assert len(ids) == 3

    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="BUG: parameters defaults to None but .get is called on it",
    )
    def test_default_parameters(self, lt):
        layer_preparation(lt, "embryo")

    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="BUG: the mesh branch reads initial_spatial_data.roots, "
        "which is not a field of the namedtuple",
    )
    def test_meshes_add_a_surface_layer(self, lt):
        lt.mesh = {
            1: {"vertices": np.eye(3), "faces": np.array([[0, 1, 2]])},
            10: {"vertices": np.eye(3) + 1, "faces": np.array([[0, 1, 2]])},
        }
        layers = layer_preparation(lt, "embryo", parameters={})
        assert [layer[2] for layer in layers] == ["points", "surface"]
        surface_kwargs = layers[1][1]
        assert surface_kwargs["name"] == "embryo_mesh"
        assert surface_kwargs["metadata"]["node_to_vertex_range"] == {
            1: (0, 3),
            10: (3, 6),
        }


def test_extract_napari_surface(lt):
    lt.mesh = {
        3: {
            "vertices": np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]),
            "faces": np.array([[0, 1, 2]]),
        },
        12: {
            "vertices": np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]]),
            "faces": np.array([[2, 1, 0]]),
        },
    }
    vertices, faces = _extract_napari_surface_from_lT(lt)
    assert vertices.shape == (6, 4)
    assert faces.shape == (2, 3)
    # Faces point to the vertices of their own mesh, stored as time
    # followed by the reversed (z, y, x) coordinates.
    triangles = [[tuple(vertices[i]) for i in face] for face in faces.tolist()]
    assert sorted(triangles) == sorted(
        [
            [(2, 3, 2, 1), (2, 6, 5, 4), (2, 9, 8, 7)],
            [(2, 0, 0, 1), (2, 0, 1, 0), (2, 1, 0, 0)],
        ]
    )
