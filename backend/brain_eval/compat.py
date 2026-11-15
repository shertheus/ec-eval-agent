"""gCastle 1.0.3 compatibility without editing installed packages.

NetworkX 3 removed the numpy_matrix aliases used by the stock gCastle simulator.
Use ndarray equivalents in this disposable algorithm/generation process, matching
the existing development environment's compatibility patch.
"""


def gcastle_networkx():
    import networkx as nx
    if not hasattr(nx,"to_numpy_matrix"):
        nx.to_numpy_matrix=nx.to_numpy_array
    if not hasattr(nx,"from_numpy_matrix"):
        nx.from_numpy_matrix=nx.from_numpy_array
