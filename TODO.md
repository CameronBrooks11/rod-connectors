# TODO

- Allow for alternates modes of input (i.e. euler angles, quaternions, etc)
- Make better system for building a connector from a series of input pipes that to decouple description of connector from the orientation specification. For example:
  - rod orientation:
    - [ x, y, z ] vector input
    - [ length, theta, phi ] spherical input
    - [ roll, pitch, yaw ] euler angle input
  - rod properties:
    - diameter
    - wall thickness
    - length
    - inner & outer facets
    - Screw hole / slot features
- Turn into named module with parameters
