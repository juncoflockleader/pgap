# Elden Ring-Inspired Gear Taxonomy

This note records the public-reference crawl used to tune `pgap-gear` breadth.
It is intentionally a taxonomy and silhouette guide, not a copy target. Generated
outputs remain original, deterministic, low-poly assets assembled from the local
module kit.

## Sources Crawled

- https://eldenring.wiki.gg/wiki/Weapons?action=raw
- https://eldenring.wiki.gg/wiki/Shields?action=raw
- https://eldenring.wiki.gg/wiki/All_Items_(Gallery)?action=raw
- Sample item description pages:
  - https://eldenring.wiki.gg/wiki/Uchigatana?action=raw
  - https://eldenring.wiki.gg/wiki/Rapier?action=raw
  - https://eldenring.wiki.gg/wiki/Halberd?action=raw
  - https://eldenring.wiki.gg/wiki/Scythe?action=raw
  - https://eldenring.wiki.gg/wiki/Twinblade?action=raw
  - https://eldenring.wiki.gg/wiki/Flail?action=raw
  - https://eldenring.wiki.gg/wiki/Greatbow?action=raw
  - https://eldenring.wiki.gg/wiki/Wooden_Greatshield?action=raw

## Crawl Summary

The public weapon category page groups armaments into many families: daggers,
throwing blades, straight/light/great/colossal swords, thrusting swords, curved
swords, backhand blades, katanas, twinblades, axes, hammers, flails, spears,
halberds, reapers, whips, fists, claws, perfume bottles, bows, crossbows,
ballistas, staves, sacred seals, torches, and shield classes.

The public shield page groups shields as torches, small shields, medium shields,
greatshields, and thrusting shields. The gallery also shows armor split into head,
chest, arms, and legs, plus talismans.

Sample descriptions imply class-level shape cues suitable for procedural recipes:

- Katana: long, curved, single-edged blade with a compact guard and longer grip.
- Thrusting sword: slender piercing blade, often with a cup or narrow guard.
- Halberd: polearm combining spear point and side axe/glaive blade.
- Reaper: long haft with a slender curved scythe blade.
- Twinblade: central grip with blades on both ends.
- Flail: handle, chain, and weighted or spiked head.
- Greatbow: oversized bow with heavy limbs and large draw profile.
- Greatshield: large reinforced defensive plate.

## Implemented Mapping

New or broadened rigid templates:

- `katana`: `uchigatana`, `wakizashi`, `great`, `nodachi`
- `thrusting_sword`: `rapier`, `estoc`, `heavy`, `stitcher`
- `twinblade`: `balanced`, `peeler`, `leaf`, `ornate`
- `hammer`: `warhammer`, `club`, `pick`, `spiked`, `great`
- `halberd`: `axe`, `glaive`, `bill`, `crescent`, `banner`
- `reaper`: `scythe`, `grave`, `halo`, `winged`
- `flail`: `spiked`, `chainlink`, `round`
- `sacred_seal`: `finger`, `order`, `clawmark`, `spiral`
- `greatbow`: `great`, `golem`, `horn`
- `crossbow`: `light`, `heavy`, `repeating`, `pulley`
- `torch`: `flame`, `ghostflame`, `sentry`, `wire`
- `claw`: `hook`, `talon`, `beast`
- `fist`: `caestus`, `spiked`, `katar`
- `perfume_bottle`: `round`, `faceted`, `fire`, `lightning`, `poison`
- `shield`: added `buckler`, `great`, `tower`, `palisade`, `thrusting`

Armor and talismans are crawled but not fully implemented in this rigid held-gear
lane. Worn armor belongs to the later skinned/deformable path described in the
gear PRD. Talismans can be added later as static accessory props once sockets and
non-hand attachment semantics are defined.
