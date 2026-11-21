default:
    @just --list

# Render the examples and check the hubs: one solid, sockets with floors, walls between bores, refusals
test:
    python3 tests/test_rod_connectors.py

# Everything CI runs, bar the tests
check: fmt-check

# Format the .scad sources with topiary (.topiary/languages.ncl)
fmt:
    git ls-files -z '*.scad' | xargs -0 -r topiary format

# Check the .scad sources are formatted, without changing them
fmt-check:
    git ls-files -z '*.scad' | xargs -0 -r -n1 topiary format --check

# Render the README picture into docs/img/
images:
    @mkdir -p docs/img
    openscad --render --camera=0,0,0,60,0,30,0 --viewall --autocenter --imgsize=800,560 --colorscheme=Tomorrow -o docs/img/hub-five-way.png examples/hub_five_way.scad
