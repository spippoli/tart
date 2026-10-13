// Rome's map overlay: city walls, archaeological sites, and ruins drawn as lines or
// areas within Roma Capitale (ISTAT 058091) and Vatican City. Run as README.md says;
// the result is © OpenStreetMap contributors, under the ODbL.
[out:json][timeout:180];
(
  area["boundary"="administrative"]["ref:ISTAT"="058091"];
  area["boundary"="administrative"]["admin_level"="2"]["ISO3166-1"="VA"];
)->.rome;
(
  wr["barrier"="city_wall"](area.rome);
  wr["historic"="citywalls"](area.rome);
  wr["historic"~"^(archaeological_site|ruins)$"](area.rome);
);
out body;
>;
out skel qt;
