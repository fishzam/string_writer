# Plugin for QGIS to Save Map Layers as Surpac String Files

- Map layer must be LineString or Point
- If layer has Z values these will be written to the string file.
- If layer has no Z values but has elevation values in field named ELEV (for example contours generated from DEM), these will be written to string file.
- If layer has no Z values and no field named ELEV, user inputed default Z value will be written to the string file.
