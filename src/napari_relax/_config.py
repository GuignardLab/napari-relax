from napari.settings import NapariSettings
from pathlib import Path
import yaml
from pydantic import Field, ConfigDict, BaseModel, field_validator


class Settings(BaseModel):

    model_config = ConfigDict(validate_assignment=True, strict=True)
    color_of_nodes: str = Field(
        default="black", description="Color of the nodes"
    )
    color_of_edges: str = Field(
        default="black", description="Color of the edges"
    )
    node_size: int = Field(default=10, gt=0, description="Size of the nodes")
    lw: float = Field(
        default=0.3, gt=0.0, description="Line width of the edges"
    )
    fontsize: int = Field(
        default=6, gt=0, description="Font size of the labels"
    )
    color_of_selection_nodes: str = Field(
        default="magenta", description="Color of the selected nodes"
    )
    color_of_selection_edges: str = Field(
        default="magenta", description="Color of the selected edges"
    )
    all_selected: bool = Field(
        default=False, description="Unselect the lineage"
    )

    @field_validator("node_size", mode="before")
    @classmethod
    def parse_node_size(cls, v):
        return int(v)

    @field_validator("fontsize", mode="before")
    @classmethod
    def parse_fontsize(cls, v):
        return int(v)

    @field_validator("lw", mode="before")
    @classmethod
    def parse_lw(cls, v):
        return float(v)

    def get_dict(
        self,
    ):
        return {
            "color_of_nodes": self.color_of_nodes,
            "color_of_edges": self.color_of_edges,
            "node_size": self.node_size,
            "lw": self.lw,
            "fontsize": self.fontsize,
            "color_of_selection_nodes": self.color_of_selection_nodes,
            "color_of_selection_edges": self.color_of_selection_edges,
            "all_selected": self.all_selected,
        }

    def reset_to_defaults(self):
        for field_name, field in Settings.model_fields.items():
            setattr(self, field_name, field.default)


class rlx_config:

    def find_path(self) -> Path:
        """Finds napari's configuration file

        Raises
        ------
        Warning
            If napari has not been initialized at any time before using this function.
        """
        nap_settings = NapariSettings().config_path
        if nap_settings:
            self.PATH = nap_settings.parent / "ReLAX_conf.yaml"
        else:
            raise Warning(
                "Please open napari before using ReLAX for the first time."
            )
        return self.PATH

    def read_config_or_default(self):
        """Reads the config file"""
        if self.PATH.exists() and self.PATH.stat():
            with open(self.PATH, "r") as conf:
                tmp = yaml.safe_load(conf) or {}
                conf = Settings(**tmp)
        else:
            conf = Settings()
        self.settings_file = conf
        self.write_config(conf.get_dict())
        return conf

    def write_config(self, settings):
        """Writes the configuration files

        Parameters
        ----------
        settings : _type_
            _description_
        """
        with open(self.PATH, "w") as conf:
            yaml.safe_dump(settings, conf)

    @property
    def current_settings(self):
        return self.settings_file

    @current_settings.setter
    def current_settings(self, settings):
        self.settings_file = self.current_settings.model_copy(update=settings)
        self.write_config(settings)

    def __init__(self) -> None:
        self.PATH: Path = None
        self.find_path()
        self.read_config_or_default()
