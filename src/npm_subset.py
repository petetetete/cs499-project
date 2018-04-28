import json
import random
import sys


if __name__ == "__main__":

    # Catch missing parameters
    if len(sys.argv) < 4:
        print("usage: npm_subset <data-file> <out-file> <size>")
        sys.exit(-1)

    # Get command line params (no error checking, just gonna believe)
    data_file = sys.argv[1]
    out_file = sys.argv[2]
    size = int(sys.argv[3])

    # Tracking variables
    keys = ["dependencies", "devDependencies"]
    edges = set()

    # Load data in to memory
    with open(data_file, "r") as file:
        data = json.load(file)  # Save json data

    # Create edgelist and save to edges set
    for package in data:
        for key in keys:
            if key in package:
                for dependency in package[key]:
                    edge = package["name"] + "\t" + dependency + "\n"
                    if edge not in edges:
                        edges.add(edge)

    # Write create edgelist
    with open(out_file, "w") as file:
        file.writelines(random.sample(edges, size))
