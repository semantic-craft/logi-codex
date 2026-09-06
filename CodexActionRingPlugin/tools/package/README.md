# I09 package workflow

`prepare_package.py` is the only projection step. It preserves the official generated
manifest shape, copies the final plugin icon and haptic sources, and maps the nine
product actions to Logitech class-named files.

The package intentionally contains no bundled Options+ profile: users assign the
their choice of eight of the nine discoverable actions to the eight slots of the Actions Ring.
`package_release.py` stages only allowlisted release content, invokes the official
LogiPluginTool `pack` and `verify` commands, and records the exact artifact size and
SHA-256.
