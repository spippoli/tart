// Roma Capitale (ISTAT 058091) and Vatican City, with their member ways' geometry.
// Run by boundary.py; the result is © OpenStreetMap contributors, under the ODbL.
[out:json][timeout:180];
(
  relation["boundary"="administrative"]["ref:ISTAT"="058091"];
  relation["boundary"="administrative"]["admin_level"="2"]["ISO3166-1"="VA"];
);
out geom;
