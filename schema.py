from pydantic import BaseModel, ConfigDict, Field


class DimensionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_number: str | None = Field(description="Part number from the datasheet.")
    max_length_mm: float | None = Field(description="Maximum package body length in millimeters.")
    max_width_mm: float | None = Field(description="Maximum package body width in millimeters.")
    max_height_mm: float | None = Field(description="Maximum package body height in millimeters.")
    pin_number: int | None = Field(description="Number of package pins.")
    evidence_page: int | None = Field(description="PDF page number used as evidence.")
    evidence: str | None = Field(description="Short explanation of the dimension symbols and values used.")


class ElectricalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_number: str | None = Field(description="Part number from the datasheet.")
    min_operating_temp_c: float | None = Field(description="Minimum operating temperature in Celsius.")
    max_operating_temp_c: float | None = Field(description="Maximum operating temperature in Celsius.")
    io_if_a: float | None = Field(description="Maximum average output current or forward current in amperes.")
    vf: str | None = Field(description="Forward voltage values with test conditions, normalized like '0.715 @1mA、0.855 @10mA'.")
    vrrm_v: float | None = Field(description="Peak repetitive reverse voltage VRRM in volts.")
    ir: str | None = Field(description="Reverse current values with test conditions, normalized like '2.5uA @75V、25nA @20V'.")
    evidence: str | None = Field(description="Short explanation of source sections and units used.")