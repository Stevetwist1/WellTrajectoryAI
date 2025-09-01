from typing import List, Optional
from pydantic import BaseModel, Field


class SurveyPoint(BaseModel):
    md: float = Field(description="Measured Depth (e.g. survey or MD)")
    inc: float = Field(description="Inclination in degrees")
    azi: float = Field(description="Azimuth in degrees")
    tvd: float = Field(description="True Vertical Depth")
    ns: float = Field(description="Northing in local grid coordinates")
    ew: float = Field(description="Easting in local grid coordinates")
    #x: Optional[float] = Field(description="X coordinate in local grid coordinates")
    #y: Optional[float] = Field(description="Y coordinate in local grid coordinates")
    class Config:
        extra = "forbid"


class DirectionalSurvey(BaseModel):
    uwi: str = Field(description="Unique Well Identifier/API number")
    survey_points: List[SurveyPoint] = Field(description="Ordered list of directional survey points")

    # Survey metadata
    operator: Optional[str] = Field(description="Operating company name")
    vendor: Optional[str] = Field(description="Trajectory service vendor")
    contact_info: Optional[str] = Field(description="Contact information for the service company (email/phone)")
    county: Optional[str] = Field(description="County where the well is located")

    method: Optional[str] = Field(description="Survey calculation method (e.g. minimum curvature)")
    north_ref: Optional[str] = Field(description="North reference (e.g. true north, grid north)")

    # Surface Hole Location (SHL)
    shl_lat: Optional[str] = Field(description="Surface Hole Location or SHL or S/H or Under the Well section: Latitude. if given in degree format, MUST BE CONVERTED TO DECIMAL FORMAT")
    shl_lon: Optional[str] = Field(description="Surface Hole Location or SHL or S/H or Under the Well section: Longitude. if given in degree format, MUST BE CONVERTED TO DECIMAL FORMAT")
    shl_x: Optional[str] = Field(description="SHL X coordinate (local grid)")
    shl_y: Optional[str] = Field(description="SHL Y coordinate (local grid)")

    # Bottom Hole Location (BHL)
    bhl_lat: Optional[str] = Field(description="BHL latitude (WGS84)")
    bhl_lon: Optional[str] = Field(description="BHL longitude (WGS84)")
    bhl_x: Optional[str] = Field(description="BHL X coordinate (local grid)")
    bhl_y: Optional[str] = Field(description="BHL Y coordinate (local grid)")

    # Additional job/site metadata
    lease_location: Optional[str] = Field(description="Lease or site location name")
    job_number: Optional[str] = Field(description="Job number or identifier")

    # Map and datum information
    map_zone: Optional[str] = Field(description="Coordinate reference system (CRS) (e.g. Texas Central, Texas North)")
    map_system: Optional[str] = Field(description="Map projection/system or map system used (e.g. State Plane, UTM)")
    geo_datum: Optional[str] = Field(description="Geodetic datum or Geodetic System or Geo Datum")
    system_datum: Optional[str] = Field(description="System datum or Vertical datum (e.g. MSL, Mean Sea Level)")
    ground_level_elevation: Optional[str] = Field(description="Ground Level or GL Elevation or GL @. Usually that will be MD reference(do not include units in the value, just the number)")
    datum_elevation: Optional[str] = Field(description="Datum elevation or MD reference  or TVD reference or the number after @ in MD Reference. (do not include units in the value, just the number)")

    # Document metadata
    date_created: Optional[str] = Field(description="Date the survey or document was created")

    class Config:
        extra = "forbid"

