# Keeps what the style draws: each feature's kind (wall or ruin), its name, and its
# OpenStreetMap id. Walls win over ruins when a feature is tagged as both.
{
  type: "FeatureCollection",
  features: [
    .features[]
    | select(.geometry.type != "Point")
    | .properties as $tags
    | {
        type: "Feature",
        geometry: .geometry,
        properties: (
          {
            kind: (if $tags.barrier == "city_wall" or $tags.historic == "citywalls" then "wall" else "ruin" end),
            id: .id
          }
          + (if $tags.name then {name: $tags.name} else {} end)
        )
      }
  ]
}
