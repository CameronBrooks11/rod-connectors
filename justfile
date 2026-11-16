default:
    @just --list

# Render the examples and check the hubs: one solid, sockets with floors, walls between bores, refusals
test:
    python3 tests/test_rod_connectors.py

# Render the README picture into docs/img/
images:
    @mkdir -p docs/img
    openscad --render --camera=0,0,0,60,0,30,0 --viewall --autocenter --imgsize=800,560 --colorscheme=Tomorrow -o docs/img/hub-five-way.png examples/hub_five_way.scad
