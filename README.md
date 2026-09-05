# Surface-Code Union-Find Decoder Visualizer

An interactive Python simulation of the **cluster-growth stage of a Union-Find decoder for quantum error correction in topological surface codes**.

The project is based on the Union-Find decoding algorithm presented by Nicolas Delfosse and Naomi H. Nickerson in *"Almost-linear time decoding algorithm for topological codes"*.

The simulator generates random errors and erasures on a square lattice, computes the resulting syndrome, and visualizes how odd-parity clusters grow and merge during the syndrome-validation process.

## Motivation

Quantum information is highly sensitive to physical errors, making efficient error correction essential for scalable quantum computing.

In surface codes, errors can be detected through stabilizer measurements that produce a **syndrome**. A classical decoder must then use this syndrome to determine how the underlying error can be corrected.

The Union-Find decoder provides an efficient approach by organizing syndrome vertices into clusters and dynamically growing and merging invalid clusters.

This project was created to better understand and visualize that process.

## What the Simulation Does

The simulator models a square lattice in which edges represent physical qubits.

For each simulation:

1. Random **Pauli-Z errors** are generated on lattice edges.
2. Random **erasures** are generated independently.
3. The syndrome is calculated from the parity of adjacent Z-errors.
4. Connected components of erased edges form the initial clusters.
5. Each cluster keeps track of the parity of the syndrome vertices it contains.
6. Odd-parity clusters grow outward by half-edges.
7. When growing clusters meet, they are merged using a Union-Find data structure.
8. Growth continues until no odd clusters remain.

The visualization allows this process to be inspected one step at a time.

## Interactive Visualization

The graphical interface allows the user to control:

- **Grid size**
- **Z-error probability (`p_z`)**
- **Erasure probability (`p_e`)**
- **Animation speed**

The simulation can be:

- Run automatically
- Advanced one growth/fusion step at a time
- Reset using the same error configuration
- Restarted with a newly generated random sample

During execution, the visualizer displays the current decoder state, including the number of erasures, syndrome vertices, odd clusters, and current growth/fusion phase.

## Union-Find Data Structure

Clusters are managed using a custom **Disjoint Set / Union-Find** implementation.

Each cluster stores:

- A parent representing the cluster tree
- The size of the cluster
- The parity of the syndrome contained in the cluster

The implementation uses:

- **Union by size** — the smaller tree is attached to the larger tree
- **Path compression** — repeated `find()` operations shorten the tree structure
- **Parity tracking** — cluster parity is updated when two clusters are merged

When two clusters are joined, their syndrome parities are combined using XOR.
