#!/bin/sh
# Phase 6: fetch OSM buildings/trees for the context extent (model extent + 200 ft) -> p6_osm_raw.json
# Overpass needs a User-Agent; retry with backoff if the server is at capacity.
Q='[out:json][timeout:60];(way["building"](30.0115,-95.5929,30.0146,-95.5879);relation["building"](30.0115,-95.5929,30.0146,-95.5879);node["natural"="tree"](30.0115,-95.5929,30.0146,-95.5879);way["natural"~"wood|tree_row"](30.0115,-95.5929,30.0146,-95.5879););out body;>;out skel qt;'
for w in 5 10 20 40; do
  curl -s -A "SH249-viz-build/1.0" --data-urlencode "data=$Q" https://overpass-api.de/api/interpreter -o p6_osm_raw.json
  head -c 20 p6_osm_raw.json | grep -q '{' && exit 0; sleep $w
done; exit 1
