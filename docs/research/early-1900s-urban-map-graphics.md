# Research: graphic language of early-20th-century city plans, and how to translate it into a MapLibre basemap

Date: 2026-10-10. Status: research, not a decision.

Audience: the agent that will define TART's map cartography style (MapLibre GL JS + PMTiles, probably the Protomaps basemap schema). Constraints come from README §13 "Visual direction" (editorial and archival, contemporary but not trend-driven, restrained; avoid designs that assume all artworks are colourful murals), README §15 (map), `CLAUDE.md` (multi-instance, WCAG 2.2 AA, status never by colour alone), ADR 0004 (MapLibre + `pmtiles`, one map module), ADR 0009 (each Instance ships its own MapLibre style file and one accent colour), and ADR 0015 (Condition signs: solid / dashed / dotted squares; approximate Location as a hatched area).

Evidence levels used below: **[source]** = stated by the cited source; **[observed]** = read by this research from a digitised scan (the scan and leaf are named, so anyone can re-check); **[unverified]** = plausible, but no source was found here.

## Summary

- Two graphic strands of c. 1890–1935 city plans matter for TART. (1) The **chromolithographed tourist plan** (Baedeker plans by Wagner & Debes, Leipzig): a black key plate, flat pink blocks, darker red for churches and public buildings, a grey-blue river with fine waterlines, spaced capitals for hills and districts, and a numbered reference grid [observed]. (2) The **monochrome line plan** (for example the *Encyclopaedia Britannica* 1911 plan of Rome, engraved by Emery Walker): white blocks outlined in black, diagonal hatching for public buildings, ruled water, and numbered keys [observed]. Strand 2 suits TART better as a base, with one warm tint borrowed from strand 1, because markers need the colour headroom.
- Reproduction technology shaped the look: copper engraving gave hairlines and sparse lettering; lithography and photolithography (from about 1860) brought flat tints, area patterns and colour plates; offset lithography (from about 1905) and type-based lettering were dominant by the early 20th century; and by the 1920s there was "a universal push to impart a modern look to maps" [source: History of Cartography vol. 6]. Limited flat plates in registration are the root of the "few flat colours + black key" aesthetic.
- Building conventions encode *material or status*, not decoration: Ordnance Survey town plans coloured masonry red and wood or iron grey, cross-hatched glass, and hatched or stippled buildings on uncoloured sheets [source]; Sanborn used yellow for frame, red for brick and blue for stone [source]; Nolli (1748) left public interiors white [source]. A modern style can reuse the *idea* (one tint for buildings, a stronger tint or a hatch for public or monumental buildings), but the Protomaps schema does not tell public from private buildings, so that layer needs extra data.
- The Rome-specific content of period plans (Aurelian Walls drawn as a heavy line, ancient remains drawn as outline-only "Avanzi di costruzioni antiche (Ruderi)", the embanked Tiber, hills in spaced capitals) is **not in the Protomaps basemap schema**: it has no city walls, archaeological sites, ruins or vineyards [source: Protomaps layers docs]. It needs a small custom overlay tileset, for example from OSM `barrier=city_wall` and `historic=archaeological_site`.
- MapLibre can do most of the translation: line casings (`line-gap-width`), waterlines (polygon `line-offset` insets), hatching (`fill-pattern` with power-of-two sprites), spaced capitals (`text-letter-spacing`), curved street names (`symbol-placement: line`). Hatching is risky at low zoom (moiré, noise under markers), and zoom expressions on patterns are evaluated only at integer zooms [source: MapLibre style spec].
- **Hatching conflict:** ADR 0015 already uses a hatched area for approximate Locations and "dashed = demolished" for disappeared Artworks. The basemap must not use the same hatch angle or density, or dashed outlines for buildings, or TART's semantic signs lose their meaning. This is the main design constraint found.
- **Colour conflict:** the period's carmine and pink for buildings competes with any red accent. Markers should be ink-dark with a paper halo; if an accent is used for *disappeared*, it should come from a hue family the basemap does not use (for example indigo). A draft token set checked for WCAG contrast is in §10.
- Typography: by the early 20th century map lettering was largely typographic; there were roman capitals for areas, italics for water, and grotesque sans for small functional text such as the legend of the 1909 Baedeker plan [observed]. All candidate typefaces checked here are SIL OFL on Google Fonts. OFL is **not** one of the three licence tiers in ADR 0011, which needs a decision.
- Avoid pastiche: no parchment textures, no aged-paper stains, no fake hand lettering, no cartouches on a live map. Borrow structure (hierarchy, restraint, block emphasis, hatching for meaning) rather than surface ageing.

## 1. Production context: how the technology made the look

- **Copper engraving**: dominant from the 16th into the 19th century. Lettering had to be incised in reverse by skilled engravers, so engraved maps were "more sparingly labeled" [source: HoC6 "Labeling of Maps", p. 738]. Its legacy is fine, even hairlines and restrained naming.
- **Lithography** (Senefelder, just before 1800): drawing in greasy ink on stone was easier than engraving. Transfer paper (autography) revived hand lettering in the mid-19th century, and photolithographic transfer arrived around 1860 [source: HoC6 "Labeling of Maps", p. 738]. Lithography "soon led to mechanical innovations … (tonal techniques, image transfer, and color printing)", and "flat and varying tones, area patterns, and colored symbols became increasingly common on maps" [source: HoC6 "Photography in Map Design and Production", p. 1148].
- **Mechanical tints**: the Ben Day tint frame (1878) let printers press raised dot or line patterns onto plates, with the cartographer marking where the tints went in non-photo blue [source: HoC6, p. 1148]. This is where the ruled and stippled area fills of the period come from.
- **Halftone and colour**: the halftone screen came in the 1890s and was combined with colour printing after 1900. Separate drawn separations for colour plates became "increasingly common after 1900" [source: HoC6, p. 1148]. Offset lithography on zinc or aluminium plates was introduced around 1905 and adopted for maps when printers abandoned copperplate engraving in Europe (commercial adoption of phototype in the 1930s) [source: HoC6 "Labeling of Maps", p. 745].
- **Hand colouring** came before mechanical colour. "Until then the printed map had been primarily a black line image on white paper, sometimes enhanced by hand coloring" [source: HoC6, p. 1148]. OS town plans were issued both coloured and uncoloured. Coloured sheets were printed from zinc, and uncoloured ones were "printed from zinc or engraved on copper" with buildings "hatched or stippled" [source: Today's Conveyancer on OS 1:500 plans; the NLS site is the better primary source but blocked automated access, see Gaps].
- **Registration**: the 1909 Baedeker plan of Rome (Internet Archive `centralitalyrome00baed_1`, leaves n762/n764/n766) shows a black key plate, a pink block plate, a darker red plate for churches and public buildings, and a grey-blue water plate. Slight misregistration of the red against the black outlines is visible at full resolution [observed]. The imprint reads "Wagner & Debes, Leipzig" [observed].
- **Implication for TART**: the period look is an artefact of *few flat plates + a fine black key*. A screen style that imitates the constraint (≤ 5 flat fills, one dark "key" colour for all line work and text) inherits the coherence without faking the defects.

## 2. Line work

Observed on the 1909 Baedeker Rome plan [observed] unless a source is cited:

| Feature | Period treatment |
|---|---|
| Streets | No fill of their own: streets are the paper left between block tints, edged by the fine black block outlines. This is a figure-ground look, not cased road lines. Main avenues read as wider gaps. |
| Block outlines | Hairline black around every block. On the EB1911 plan, blocks are outlined only, without fill [observed]. |
| Railways | Double line with alternating black and white segments ("chequered" track). Several parallel tracks are drawn as parallel chequered lines. |
| Tramways | A thin single black line along the street (inferred from lines labelled "Tramw." near Porta Tiburtina) [observed; identification tentative]. |
| City walls | The Aurelian Walls are a heavier black line with small regular projections (towers) and gaps at the gates. The Leonine and Janiculum walls are drawn similarly. |
| Water edges | River banks are firm dark lines; inside them, many fine **waterlines** run parallel to the bank and fill the channel. |
| Relief | Almost suppressed in the city: hills are carried by spaced-capital names (MONTE PALATINO, MONTE AVENTINO, M. CAPITOLINO) rather than hachures or contours. |
| Planned or undeveloped streets | Outer districts show streets as double outlines around unfilled plots. Reading these as planned or unbuilt is TART's interpretation [unverified]. |
| Neatline | A thin inner line and a heavy outer rule, with the grid labelled on the border in Roman numerals (I–III) and with the scale on the side margins. |

- **Line hierarchy is carried by weight, not hue.** All line work is in the black key. Hue is reserved for area plates.
- **Contours vs hachures**: Italian state topographic sheets (IGM 1:25,000 "tavolette") were the national reference series from Unification. The later 25V series is published in one colour (black), three (black, bistre, blue) or five colours (adding green and red, with main roads red and woods green) [source: uniparthenope IGMI production notes; units.it course slides]. At city-plan scale, period tourist plans largely leave relief out [observed]. **Recommendation:** no hillshade or contours in TART's city view. If relief is wanted for Rome's hills, use a very light hillshade only at z ≤ 13 [unverified as a period practice].

## 3. Fills and hatching

- **Buildings by material or status**:
  - OS 1:500 coloured plans: masonry red, wood or iron grey, glass cross-hatched; on uncoloured sheets buildings were hatched or stippled. Interior layouts of public buildings appear on plans published before 1880 [source: Today's Conveyancer; the NLS symbol key lists "interior layout and seating" for public buildings and "cross-hatched" for glass, per search-result summary of maps.nls.uk/townplans/symbols.html].
  - Sanborn fire-insurance key (1908–1950 sheets): yellow frame, red brick, blue stone, grey iron, brown adobe or fire-proof [source: University of Utah Sanborn collection key].
  - Baedeker 1909 Rome: ordinary blocks in flat pink; churches, palaces, ministries and other named public or monumental buildings in a darker, more saturated red, often with the building plan visible (Pantheon rotunda, Colosseum ellipse) [observed]. On the southern sheet of the same copy (n766) blocks are in a grey tint, not pink [observed; reason not established].
  - EB1911 Rome (Emery Walker): ordinary blocks are white with black outlines; numbered public buildings carry diagonal hatching; the Tiber is ruled with close horizontal lines [observed].
  - Nolli 1748 (the canonical Rome precedent): private buildings shaded, while streets, piazzas, courtyards and enterable church interiors are left white [source: Wikipedia "Giambattista Nolli"].
- **Ruins and archaeological areas** (very relevant for Rome): the 1909 Baedeker plan has a single legend entry, "Avanzi di costruzioni antiche (Ruderi)", with an outline-only symbol. The Forum, Palatine, Baths of Caracalla and Colosseum are drawn as black outlines on bare paper, without the block tint [observed]. Lanciani's *Forma Urbis Romae* (1893–1901, 46 sheets, 1:1000) distinguishes ancient (black), early-modern after Nolli (red) and modern c. 1893 (blue) [source: Wikipedia "Rodolfo Lanciani"; sources disagree on the meaning of red and blue, see Gaps].
- **Gardens and parks**: the stipple of small open circles stands for trees in villas and gardens (Villa Borghese, Villa Doria Pamphili, Gianicolo), and garden paths are drawn as fine double lines [observed].
- **Cemeteries, vineyards**: OS and IGM legends had dedicated signs; vineyards ("Vigna") appear on the Rome plan only as names on open ground [observed]. The Protomaps landuse layer has `cemetery` but no `vineyard` [source].
- **Water tint**: a grey-blue flat tint plus waterlines (Baedeker) or ruling alone (EB1911) [observed].

## 4. Colour palettes

Typical structure: one dark key (warm black) for all line work and lettering; one warm tint for built areas (pink, salmon or carmine); one stronger red for public or monumental buildings; a muted blue or grey-blue for water; green or tree stipple for parks; a cream paper.

Values sampled from the 1909 Baedeker scan (`centralitalyrome00baed_1`, leaf n764, central strip; medians of pixel classes; script-based) [observed]:

| Role | Raw scan median | Paper-normalised estimate* |
|---|---|---|
| Paper | `#C3BBA9` | `#E6E0CF` (assumed reference) |
| Block pink | `#B88571` | ≈ `#D9A08A` |
| Light pink (lighter half) | `#C59682` | ≈ `#E8B49F` |
| Public / monumental red (darkest quartile of reds) | `#814837` | ≈ `#985744` |
| Key "black" | `#361C0F` | ≈ `#3F2212` (warm brown-black) |
| Grey mid-tones (water, outlines, anti-aliasing) | `#827D6F` | ≈ `#9A9483` |

\* Normalised by assuming that the scanned paper should read as a light cream. These are **approximations**: the scan is a camera capture under warm light, JPEG-compressed, and pixel classes mix anti-aliased line work. Do not treat them as the printed ink colours.

- **Paper ageing vs original**: digitised plans show yellowed paper, faded reds and fox marks. The original stock was lighter. A style that copies the *aged* colour reads as "antique" (pastiche); one that copies the *intended* relationships (light paper, mid tint, dark key) reads as "archival". **Recommendation:** use an off-white, very slightly warm paper (L* ≈ 94–96), not a yellow-brown parchment.
- **Modern reference**: Esri's Vintage Shaded Relief basemap pairs hand-painted public-domain hillshades with papery ocean texture and pencil-like strokes [source: search-result summary of Esri ArcGIS blog, 2019, blocked to direct fetch]. It is an example of the texture-heavy direction that this document recommends *against* for TART's city view.

## 5. Typography

- **Technology**: by the early 20th century "typographic lettering had become the dominant means of labeling maps". Hand lettering survived with mechanical aids (stencils, Leroy templates, Ames guide), and the German Rundschrift (Soennecken) was used for some maps and atlases in Austria, Italy and Germany [source: HoC6 "Labeling of Maps", pp. 738–744]. In a 1929 debate on Ordnance Survey lettering, Withycombe argued for classical roman and italic forms and against modern serif faces "such as Bodoni" and against sans serif faces. A discussant noted that serifs suit larger map type and sans serif works at small sizes, and the acceptance of sans serif "presaged a general shift to sans serif typefaces for maps" [source: HoC6, p. 746].
- **Conventions** [source: Wikipedia "Typography (cartography)", citing Imhof 1962/1975, Wood 2000, Dent et al. 2009, Slocum et al. 2009]:
  - italic for hydrographic features;
  - letter-spacing to spread area labels across their extent, but not for line labels;
  - capitals for larger or special features;
  - labels follow the direction of line features and avoid sharp bends;
  - ribbon-like areas are labelled along their main axis with a slight curve.
  Imhof's aims are legibility, association, conflict avoidance, extent, hierarchy and distribution (Imhof, "Positioning Names on Maps", *The American Cartographer* 2(2):128–144, 1975).
- **Observed on the 1909 Baedeker plan** [observed]:
  - Title "ROMA": shaded or outlined display capitals.
  - Hills and quarters (MONTE PALATINO, EMPORIO, Prati di Castello): widely spaced roman capitals, often curved along the feature.
  - River: "TEVERE" in very widely spaced capitals following the channel.
  - Streets: small upright or sloped roman lower-case, set along the street axis and curving with it, abbreviated ("V.", "Pza", "Lungo Tev.").
  - Buildings: small roman, abbreviated ("Pal.", "S.M.").
  - Grid numbers: bold upright numerals.
  - Legend and scale text: a spaced grotesque sans ("Avanzi di costruzioni antiche (Ruderi)", "Metri").
- **Observed on the EB1911 plan** [observed]: street names in condensed sans capitals inside the street; italic for "Isola Tiberina"; spaced roman capitals for MONTE PALATINO.
- **IGM lettering practice**: no source on IGM lettering norms was found. IGM published "Segni convenzionali per le levate di campagna" (1:25,000 and 1:50,000; editions 1936, 1941, 1948) and, from 1950, "Segni convenzionali e norme sul loro uso" [source: BL and IGN-Spain catalogue records via search]. These are the documents to consult [unverified content].

Candidate open-licence typefaces. All are SIL OFL per Google Fonts `METADATA.pb`, checked 2026-10-10. "Latin-ext" means the family is published with the latin-ext subset; Italian needs only à è é ì ò ù (and capitals), which are in Latin-1 (glyph range 0–255).

| Family | Character / period link | Styles | Fit for map labels |
|---|---|---|---|
| Old Standard TT | "Modern (classicist)… very commonly used in… late 19th and early 20th century" (designer's description) | 400, 700, italic; latin-ext | Strong period voice; thin hairlines may break up under SDF rendering at small sizes [unverified, test]. Good for district caps and the title. |
| Spectral | Screen-first serif, 7 weights + italic + small caps | latin-ext | Robust small-size serif; less period-specific; good for street names. |
| Source Serif 4 | Transitional, after Fournier; optical-size axis | italic; latin-ext | Robust; `opsz` helps small labels if static instances are generated for glyph PBFs. |
| EB Garamond / Cormorant Garamond | Old-style revivals | italic; latin-ext | Elegant but delicate at map sizes; Cormorant is too fine for labels. |
| IM Fell (Double Pica) | 17th-century Fell types | italic; latin-ext (Double Pica only) | Too antique and textured; reads as pastiche. Not recommended. |
| Libre Caslon Text | Based on 1950s advertising Caslon | italic; latin-ext | Off-period; usable but not distinctive. |
| Bodoni Moda | Didone, `opsz` axis | italic; latin-ext | High contrast; hairlines vulnerable on screen; Withycombe's 1929 objection applies. Not recommended. |
| Libre Franklin | "interpretation… of the 1912 Morris Fuller Benton classic" (Franklin Gothic) | italic; variable weight; latin-ext | Period-true American gothic; good for legend, scale and small functional labels. |
| News Cycle | Revival of "1908-era News Gothic" | 400, 700 only, no italic; latin-ext | Period-true; narrow; good for dense small labels; no italic is a limitation. |
| Work Sans | "based loosely on early Grotesques" | italic; variable; latin-ext | Screen-optimised grotesque; neutral. |
| Alegreya / Alegreya Sans | Calligraphic humanist serif + sans pair | many weights; latin-ext | Coherent pair; slightly literary rather than cartographic. |

MapLibre glyphs are SDF glyph sets in PBF, fetched per 256-codepoint range from a `glyphs` URL template [source: MapLibre style spec "Glyphs"]. Every chosen weight and style must be pre-built into PBF ranges and served next to the PMTiles.

## 6. Symbology and legend conventions

- **Churches**: named in "S." or "SS." abbreviations, with the building plan in the red public tint; the Pantheon and Colosseum are drawn by plan shape, not icons [observed]. Many period plans also use a small cross [unverified for the Baedeker Rome plan].
- **Stations**: named large ("Stazione di Termini", "Stazione di Trastevere") at the rail termini [observed].
- **Numbered keys and grids**: the Baedeker plan has a reference grid with large bold numbers (1–36 per strip) and Roman-numeral rows, tied to the street index printed in the guide [observed]. The index "of the principal streets and public buildings" is a Baedeker feature [source: MU Library Treasures, Paris 1905 guide]. EB1911 numbers public buildings in black squares keyed to a list [observed].
- **Scale**: a representative fraction ("1:11400") plus a segmented scale bar in metres with alternating fills [observed].
- **North arrow, cartouche**: absent on the Baedeker strips (north-up is implied) [observed]. A live web map should not add decorative cartouches.
- **Borders**: double neatline (thin + heavy) [observed].

## 7. Generalisation and content selection

- Period plans at roughly 1:10,000–1:15,000 show **blocks**, not individual buildings, except where a building is named or monumental. Then its footprint, and sometimes its plan, is shown [observed, Baedeker 1909 and EB1911].
- Naming is dense in the historic centre (streets, churches, palazzi) and sparse in expansion areas [observed].
- Tourist plans emphasise landmarks: Baedeker's plans are cited as "the famous urban plans highlighting urban landmarks" [source: HoC6 "Urban Mapping", p. 1650].
- Relief, vegetation detail and utilities are omitted or minimised; open land in the suburbs is plain paper with a few names (villas, vigne, osterie) [observed].
- **For TART**: the archive's content is the Artworks. The basemap should behave like the period plan's *base plates*: blocks, water, green, the main street names and the district names. POIs, shops and transit icons should be off by default. Protomaps' flavors ship POI icons on `light` and `dark` only; the `white`, `grayscale` and `black` flavors are meant for data visualisation [source: Protomaps "Basemap Flavors"].

## 8. Rome specifics

- **Rioni**: 22 rioni, numbered with Roman numerals from I (Monti) to XXII (Prati). Esquilino became the 15th in 1874. Prati (1921) was the last, and the only one outside the walls of Urban VIII [source: Wikipedia "Rioni of Rome"]. Benedict XIV's reorganisation placed marble boundary plaques on facades (1744 per Wikipedia; one source gives a chirograph of 18 May 1743) [source: Wikipedia; Senato "Antiquorum habet" on Roisecco]. The 1909 Baedeker plan names hills and quarters (for example "Prati di Castello", "Esquilino", "Emporio") rather than drawing rioni boundaries [observed].
  - ADR 0009 says Areas such as Rome's rioni are archive content, not configuration. If the basemap shows rioni labels from OSM tiles, they may diverge from the archive's Area records (see Open questions).
- **Tiber and muraglioni**: the embankment walls were begun in 1876 after the 1870 flood and completed in 1926, and they demolished riverside fabric such as the Ripetta harbour [source: Turismo Roma "Le lapidi delle inondazioni"; Museo di Roma in Trastevere exhibition text]. On the 1909 plan the "Lungo Tevere" roads are drawn and named along both banks [observed]. The basemap Tiber is today's embanked river. A historic-style rendering should show the hard embankment as a firm double edge (wall + lungotevere road), not a soft natural bank.
- **Aurelian Walls**: built AD 271–275 under Aurelian, about 19 km long [source: Wikipedia "Aurelian Walls"]. On the 1909 plan they are a heavy black line with tower ticks and named gates ("Porta S. Lorenzo", "Porta S. Sebastiano") [observed]. They are a primary orientation device for Rome, and they are absent from the Protomaps schema.
- **Archaeological zones**: Forum, Palatine, Baths of Caracalla and others are drawn outline-only on bare paper [observed]. Lanciani's *Forma Urbis Romae* (1893–1901) is the period's archaeological base plan [source]. Today the large Appia Antica area is mostly park or landuse in OSM [unverified for Protomaps output].
- **Planning context**: the 1909 regulatory plan by Edmondo Sanjust di Teulada established the first expansion of the city outside the Aurelian Walls [source: Wikipedia]. The 1931 plan was approved by R.D.L. 6 July 1931 n. 981, converted by L. 24 March 1932 n. 355 [source: Normattiva]. Marcello Piacentini is widely credited as a principal author [source: Gruppo dei Romanisti biography]. Copies of the plates of either plan in an accessible digitised form were not located [Gaps].
- **Baedeker Rome plan**: in the 1909 English edition (15th, Leipzig) the large plan of Rome is on three folding strips at 1:11,400, by Wagner & Debes, Leipzig [observed; edition details per HathiTrust/Yale catalogue records]. The 1930 English *Rome and Central Italy* lists 62 plans and diagrams [source: NLI catalogue].

## 9. Translation to a modern vector style (MapLibre)

| Historic convention | MapLibre technique | Notes and pitfalls |
|---|---|---|
| Paper | `background-color` | Flat colour. `background-pattern` is possible (sprite image width and height a power of two, 2–512) [source], but texture adds noise under markers and reads as pastiche. Avoid. |
| Block tint (figure-ground) | z12–14: `landuse` kinds `residential`, `commercial` etc. and `landcover: urban_area` filled with the block tint; z15+: `buildings` filled | Protomaps has no block polygons and buildings come in at z15+ [source: Protomaps layers]. True block polygons would need a custom derived tileset [unverified effort]. |
| Public or monumental red | Separate `fill` layer filtered on buildings with a church, public or monument tag | Protomaps `buildings` has kinds only (`building`, `building_part`, `address`) [source]. Needs a custom overlay or building-to-POI joining. Defer. |
| Hatching for public buildings | `fill-pattern` (data-driven supported in GL JS) with a power-of-two sprite at `pixelRatio` 2 | Zoom expressions are evaluated only at integer zooms [source]. Patterns at low zoom create moiré. **Collides with ADR 0015's hatched approximate-Location area.** Use only at z ≥ 16, with a different angle and lower contrast, or not at all. |
| Block outlines (hairline key) | `fill-outline-color` (1 px) or a `line` layer on buildings | `fill-antialias` must be on for the outline. Keep the key colour, not pure black. |
| Street casings | Streets as the paper colour with `line-gap-width` or two stacked line layers (casing below, fill above) | The period look is "paper street between tinted blocks". Casing colour should be ≥ 3:1 against paper (see §10). |
| Railway chequer | Two line layers: dark wide line + light `line-dasharray` on top | `line-dasharray` units are line widths, zoom-dependent values are evaluated only at integer zooms, and it is not data-driven in MapLibre Native [source]. |
| Tramway | Thin solid line (`kind_detail: tram`) [source: Protomaps] | Low priority; Rome trams exist today. |
| City walls with towers | Line + `symbol` layer placing a small square icon with `symbol-placement: line` and `symbol-spacing` | Needs custom data (OSM `barrier=city_wall`). |
| Ruins outline-only | `line` on custom `historic=archaeological_site` / `historic=ruins` polygons; no fill or paper fill | Custom overlay. Labels in spaced small caps. |
| Waterlines | 3–4 `line` layers on water polygons with increasing positive `line-offset` (for polygons a positive offset is an inset) [source], thin, fading opacity, z ≥ 14 | Cheap and characteristic. Check performance on large water polygons. Hide at low zoom. |
| Tree stipple | `fill-pattern` dot sprite on parks at z ≥ 15; flat green below | Stipple competes with dotted *unknown* marker squares (ADR 0015). Keep dots tiny, low contrast, and park-only. |
| Spaced capitals for districts and hills | `text-transform: uppercase`, `text-letter-spacing` 0.2–0.4 em [property source] | Use for area labels only, not line labels (Imhof). |
| Curved street names | `symbol-placement: line`; `text-max-angle` small | Period streets were abbreviated ("V.", "Pza"). Don't abbreviate: abbreviations hurt i18n and accessibility. |
| Italic hydronyms | Separate italic font in `text-font` | Requires italic glyph PBFs. |
| Reference grid and numbered keys | **Do not translate** | A live map has search and a list panel (README §15). A grid is clutter. |
| Hand lettering, shaded title capitals, cartouche, neatline | **Do not translate** on the live map | Possibly for a print or export view later. |

**What does not translate well**:
- dense hatching or stipple at z < 15 (moiré and shimmer during zoom);
- hairline serifs under SDF rendering;
- multi-plate misregistration;
- yellowed paper;
- aliasing of 1 px diagonal hatch on non-retina screens [unverified, test on target devices].

**Pitfalls**:
- *Pastiche or kitsch*: textures, distressed type, sepia filters, "Ye Olde" fonts (IM Fell). README §13 asks for "contemporary but not trend-driven".
- *Legibility*: period street labels were tiny and abbreviated, while web labels need ≥ 4.5:1 contrast (WCAG 1.4.3) and haloes over tints.
- *Marker contrast*: a pink and red basemap absorbs red markers; markers must be the strongest marks on the map.
- *Semantic collision*: as noted for ADR 0015, dashed and hatched patterns already carry meaning in TART.
- *Dark mode*: no period precedent. Treat it as an "ink" negative: a dark warm paper, light key line work, near-invisible block tint. Don't invert the pink.

**Staying "contemporary but not trend-driven"**: keep the *structure* of the period plan (figure-ground blocks, a single key colour, weight hierarchy, a restrained flat palette, typographic hierarchy) and render it crisply. The archival tone then comes from discipline, not from effects. Huffman's period-style work is an example of deliberate historical stylisation as a one-off art piece [source: ICA MapCarte 292/365], a different goal from a daily-use basemap.

**Accessibility**:
- WCAG 1.4.1 (use of colour): the Condition must be carried by sign and word, as already decided in ADR 0015.
- WCAG 1.4.11 (non-text contrast, 3:1) applies to graphics required to understand content: markers, selected state, clusters, approximate-area outline. A basemap tint that only gives context can be lower contrast, but street casings that users need for orientation should aim for 3:1.
- WCAG 1.4.3 (text, 4.5:1; large text 3:1) applies to all labels against *every* fill they can sit on.
- Colour-blind safety: a warm (red, pink, ochre) basemap with a blue-family accent keeps the accent separable on the blue–yellow axis that most colour-vision deficiencies preserve [unverified; reasoning, test with a simulator].

## 10. Recommendations for TART's style agent (recommendations, not decisions)

**R1. Base strand.** Build the light style on the monochrome line-plan strand (white or paper blocks with key outlines, as in EB1911), plus **one** warm block tint borrowed from Baedeker. Show public or monumental buildings by a slightly stronger tint, not by hatching, until ADR 0015's approximate-area hatch is drawn. Then choose a basemap hatch (if any) that is visibly different from it.

**R2. Draft palette tokens** (light; contrast ratios computed with the WCAG relative-luminance formula by a local script):

| Token | Light | Dark | Use |
|---|---|---|---|
| `map.paper` | `#F4EFE4` | `#1D1B19` | background, street fill, ruin interiors |
| `map.block` | `#EBDCD2` | `#2A2522` | built areas z12–14, buildings z15+ |
| `map.block.public` | `#D9B8A8` | `#3A2F2A` | public or monumental buildings (if data exists) |
| `map.park` | `#E2E6D3` | `#232821` | parks, gardens, cemeteries (cemeteries + small cross pattern at z ≥ 16, optional) |
| `map.water` | `#D3DEE0` | `#1B2427` | water fill |
| `map.waterline` | `#9DB2B8` | (tbd) | inset waterlines z ≥ 14 (decorative) |
| `map.ink` | `#2A2521` | `#E9E2D6` | key line work, walls, rail base |
| `map.casing` | `#857A70` | `#7A7068` | street casings, block outlines (3.65:1 on paper; 3.13:1 on block, light) |
| `map.ruin.line` | `#7A6C60` | `#9C8E80` | archaeological outlines (4.4:1 on paper, light) |
| `map.label.street` | `#3A332E` | `#D8CFC3` | street names (≥ 6.7:1 on every light fill) |
| `map.label.district` | `#6A5546` | `#B9A694` | rioni and hill caps (≥ 5.2:1 on paper/block; 3.8:1 on public tint, OK only for large text) |
| `map.label.water` | `#3F5F69` | `#9FBAC2` | italic hydronyms (5.0:1 on water, light) |
| `marker.ink` | `#1F1B18` | `#F4EFE4` | Condition squares, with a 2 px `map.paper` halo (≥ 9.2:1 on every light fill) |
| `marker.accent` (Instance accent, ADR 0009) | e.g. `#2E3F8F` | e.g. `#9DB0FF` | redundant accent for *disappeared* (≥ 5.1:1 on every light fill) |

Fill-vs-paper ratios are deliberately low (1.06–1.6), because tints are context. Their boundaries are carried by the casing and outline lines, so no information depends on telling tints apart. Re-run the contrast checks if any token changes. The Instance accent should be validated against *all* basemap fills, not only the UI backgrounds that ADR 0009 checks today.

**R3. Typography hierarchy** (example pairing: Spectral or Source Serif 4 for names, Libre Franklin for functional text; Old Standard TT is an option for district caps if it survives SDF tests):

| Level | Style | Zoom |
|---|---|---|
| City or archive name | not on the map (UI chrome) | — |
| Rioni / quarters / hills | serif caps, letter-spacing 0.25–0.35 em, `map.label.district`, 11–14 px | z12–15 |
| Major streets | serif regular, 11–12 px, along line | z14+ |
| Minor streets | serif regular, 10–11 px | z16+ |
| Water | serif italic, letter-spaced for rivers, `map.label.water` | z11+ |
| Parks, villas, ruins | serif italic or small caps, 10–11 px | z15+ |
| Stations, functional | sans (Libre Franklin) 10–11 px | z14+ |

Labels get a `map.paper` halo of 1–1.5 px. Use no abbreviations. Labels come from tile `name` fields, in the language the data provides. That is not the UI language, which matches the `CLAUDE.md` rule not to assume content language equals UI language.

**R4. Layer-by-layer treatment**:

| Layer (Protomaps unless noted) | z10–12 | z13–14 | z15–16 | z17+ |
|---|---|---|---|---|
| `earth` / background | paper | paper | paper | paper |
| `water` | flat water | + firm bank line | + 2–3 inset waterlines | + 3–4 waterlines |
| `landuse` park, garden, cemetery | flat park | flat park | + faint tree stipple | stipple |
| Built area (`landuse` / `landcover urban_area`) | block tint | block tint | → replaced by `buildings` | — |
| `buildings` | — | — | block tint + casing outline | + public tint (if data) |
| `roads` highway / major | ink single line | paper fill + casing | paper + casing | paper + casing |
| `roads` minor / path | hidden | thin casing only | paper + casing | + paths as thin solid lines (no dashes, see R5) |
| `roads` rail | thin ink | chequer (ink + paper dash) | chequer | chequer |
| Custom: city walls | ink 1.5 px | ink 2 px | + tower ticks | + gates labelled |
| Custom: archaeological / ruins | hidden | outline only | outline + italic label | outline + label |
| `boundaries` (locality) | hidden or thin dot-dot | hidden | hidden | hidden |
| `places` neighbourhood (rioni) | — | spaced caps | spaced caps, lighter | hidden |
| `pois` | off | off | off | off (selected landmarks optional) |
| TART markers / clusters | clusters | clusters → squares | squares | squares + approximate-area hatch |

**R5. Markers vs basemap.**
- Markers are the only saturated or darkest elements on the map.
- Use ADR 0015's solid / dashed / dotted squares in `marker.ink` with a paper halo, so they read on blocks, parks and water alike.
- Reserve 45° hatching and dashed outlines for TART semantics: the basemap uses neither.
- Clusters are ink discs or squares with paper numerals (≥ 4.5:1).
- A selected marker gets a size change plus an outline ring, never colour alone.

**R6. Per-Instance configurability.**
- Ship the palette as a Protomaps-style Flavor object (the `@protomaps/basemaps` Flavor interface has keys such as `background`, `earth`, `park_a`, `water`, `buildings`, `major`, `minor_a`, `railway`, `roads_label_major`, `city_label` and font names `regular` / `bold` / `italic`) [source: `@protomaps/basemaps` 5.7.2 `src/flavors.ts`, BSD-3-Clause].
- Then post-process the generated layers to add the TART extras: waterlines, chequered rail, an optional overlay for walls and ruins.
- The Rome extras (walls, archaeology) are an Instance-level overlay source in the Instance's style file (ADR 0009), not platform code.
- Another city reuses the same tokens and may add its own overlays (for example fortifications).

**R7. Dark mode.** An "ink" negative using the dark tokens above: no pink, waterlines and stipple off, casings and labels at the stated contrast.

**R8. Prototype before deciding.** Build three z14 and z17 screenshots of central Rome (Campo Marzio, Forum, Prati) with real markers in all three Condition signs plus an approximate area. Test them on a low-DPI screen, in greyscale, and with a deuteranopia simulator.

## Open questions

1. Is OFL acceptable for fonts under ADR 0011? Its dependency tiers list MIT/BSD/Apache-2.0/ISC/PSF/Zlib, LGPL/MPL and GPL/AGPL, not OFL. Fonts served as glyph PBFs are assets, not linked code, but this needs an explicit decision.
2. Should the Rome overlay for walls and archaeology be built (OSM extract → small PMTiles) in the MVP, or should the style ship without it at first?
3. Should the basemap distinguish public or monumental buildings at all (data cost), or keep a single block tint?
4. Rioni labels: from OSM tiles (may diverge from the archive's Area records, ADR 0009) or from the archive's own Areas as a TART layer?
5. Which hatch angle and density does ADR 0015's approximate-area sign use? The basemap pattern choices depend on it.
6. Is a print or export view (with neatline, scale bar and grid) in scope later? Some non-translatable conventions could live there.

## Gaps and unverified items

- NLS (maps.nls.uk) and David Rumsey (davidrumsey.com) blocked automated fetching (CAPTCHA or "verify access"). OS symbol details are therefore from a secondary article plus search-result summaries of the NLS key. No OS "characteristic sheet" for town plans was read directly.
- No accessible digitised plates of the 1909 Sanjust or 1931 PRG were inspected. A Commons upload of the 1909 PRG exists ("Piano regolatore roma 1909.jpg", CC BY-SA, user upload) but was not analysed. Touring Club Italiano period plans of Rome were not located online.
- IGM lettering norms and the full "segni convenzionali" tables of 1890–1935 were not found online. Only catalogue titles and later 25V colour versions are cited.
- Lanciani colour meanings: Wikipedia and the Rumsey catalogue (per search summary) say red = early modern (Nolli) and blue = modern c. 1893. Another site says blue = planned changes.
- Paris (Service du Plan), Vienna and Berlin period plans were not researched in this pass.
- Sampled hex values are approximations from one camera-captured scan.
- MapLibre pattern rendering details (pixel-constant pattern size across zoom; SDF degradation of hairline serifs) are practitioner knowledge, not verified against docs here. Test them.

## Sources

- History of Cartography vol. 6 (ed. Monmonier, University of Chicago Press, 2015), free online: https://www.press.uchicago.edu/books/HOC/HOC_V6/Volume6.html
  - "Labeling of Maps" (pp. 738–747): https://www.press.uchicago.edu/books/HOC/HOC_V6/HOC_VOLUME6_L.pdf
  - "Photography in Map Design and Production" (pp. 1146–1148): https://www.press.uchicago.edu/books/HOC/HOC_V6/HOC_VOLUME6_P.pdf
  - "Urban Mapping" (pp. 1649–1652): https://www.press.uchicago.edu/books/HOC/HOC_V6/HOC_VOLUME6_U.pdf
- Baedeker, *Central Italy and Rome*, 15th ed., Leipzig 1909 (University of Toronto copy), plan of Rome on leaves n762, n764, n766: https://archive.org/details/centralitalyrome00baed_1 (page images: https://archive.org/download/centralitalyrome00baed_1/page/n764_w3000.jpg)
- HathiTrust record, 1909 edition: https://catalog.hathitrust.org/Record/000349715
- National Library of Ireland, Baedeker *Rome and Central Italy* 1930: https://catalogue.nli.ie/Record/vtls000400281
- Wagner & Debes background: https://antiquemapsandprints.com/collections/baedeker-karl-wagner-debes ; https://en.wikipedia.org/wiki/Baedeker
- Baedeker Paris guide (street and public-building index): https://mulibrarytreasures.wordpress.com/2025/08/01/a-guide-to-paris-by-karl-baedeker-sons/
- *Encyclopaedia Britannica* 11th ed. (1911), "Rome" plan, engraved by Emery Walker (public domain): https://commons.wikimedia.org/wiki/File:EB1911_Rome_-_map_(modern).jpg
- OS 1:500 town plans, building colours and hatching: https://todaysconveyancer.co.uk/1500-scale-town-plans-big-is-beautiful/
- NLS OS town plans symbols and info (blocked to fetch; cited via search summary): https://maps.nls.uk/townplans/symbols.html ; https://maps.nls.uk/os/townplans-england/info.html
- Digimap Historic town plans list: https://digimap.edina.ac.uk/webhelp/historic/about_historic_maps/townplans_list.htm
- Sanborn map colour key (University of Utah): https://collections.lib.utah.edu/details?id=1697159
- Nolli map: https://en.wikipedia.org/wiki/Giambattista_Nolli
- Lanciani, *Forma Urbis Romae*: https://en.wikipedia.org/wiki/Rodolfo_Lanciani ; https://sights.seindal.dk/other-images-sources/lanciani-forma-urbis-romae/
- Rioni of Rome: https://en.wikipedia.org/wiki/Rioni_of_Rome ; https://antiquorum-habet.senato.it/index.php/character-witness/roisecco-gregorio-it ; https://turismoroma.it/it/node/49220
- Tiber embankments: https://turismoroma.it/it/le-lapidi-delle-inondazioni ; https://www.museodiromaintrastevere.it/sites/default/files/storage/original/application/3fc36572b357d884c04274cea1449130.pdf
- Aurelian Walls: https://en.wikipedia.org/wiki/Aurelian_Walls
- 1909 plan, Sanjust: https://en.wikipedia.org/wiki/Edmondo_Sanjust_di_Teulada
- 1931 plan law: https://www.normattiva.it/eli/id/1932/04/25/032U0355/CONSOLIDATED/20091216 ; Piacentini: https://www.gruppodeiromanisti.it/wp-content/uploads/2015/04/PIACENTINI-Marcello.pdf
- IGM: production and series colours: https://elearning.uniparthenope.it/pluginfile.php/178130/mod_resource/content/2/3.%20La%20produzione%20IGMI.pdf ; https://moodle2.units.it/pluginfile.php/501711/mod_resource/content/0/Carto_4_cartografia-naz-reg.pdf ; segni convenzionali catalogue records: https://searcharchives.bl.uk/catalog/040-004299417 ; https://www.ign.es/web/catalogo-cartoteca/resources/pdfcards/card025162.pdf
- Map typography conventions (Imhof, Wood, Dent et al.): https://en.wikipedia.org/wiki/Typography_(cartography) ; Imhof, E. (1975) "Positioning Names on Maps", *The American Cartographer* 2(2):128–144.
- Esri Vintage Shaded Relief (via search summary; direct fetch 403): https://www.esri.com/arcgis-blog/?p=440422
- Daniel Huffman, "The Ways of the Framers" (ICA MapCarte 292/365): https://mapdesign.icaci.org/2014/10/mapcarte-292365-the-ways-of-the-framers-by-daniel-huffman-2011/
- MapLibre Style Spec, layers: https://maplibre.org/maplibre-style-spec/layers/ ; sprites: https://maplibre.org/maplibre-style-spec/sprite/ ; glyphs: https://maplibre.org/maplibre-style-spec/glyphs/
- Protomaps basemap layers: https://docs.protomaps.com/basemaps/layers ; flavors: https://docs.protomaps.com/basemaps/flavors ; Flavor interface (`@protomaps/basemaps` 5.7.2, `src/flavors.ts`): https://unpkg.com/@protomaps/basemaps@5.7.2/src/flavors.ts
- OSM tags for the Rome overlay: https://wiki.openstreetmap.org/wiki/Tag:barrier%3Dcity_wall ; https://wiki.openstreetmap.org/wiki/Tag:historic%3Darchaeological_site ; https://wiki.openstreetmap.org/wiki/Tag:historic%3Druins ; https://wiki.openstreetmap.org/wiki/Tag:landuse%3Dvineyard
- Google Fonts metadata (licence, subsets, descriptions), `google/fonts` repository `ofl/<family>/METADATA.pb` and `DESCRIPTION.en_us.html`, e.g. https://raw.githubusercontent.com/google/fonts/main/ofl/oldstandardtt/METADATA.pb ; https://raw.githubusercontent.com/google/fonts/main/ofl/librefranklin/DESCRIPTION.en_us.html ; https://raw.githubusercontent.com/google/fonts/main/ofl/newscycle/DESCRIPTION.en_us.html
- WCAG 2.2 Understanding: 1.4.1 https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html ; 1.4.3 https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html ; 1.4.11 https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
- TART internal: README §13 and §15; ADR 0004, 0009, 0011, 0015 in `docs/adr/`.
