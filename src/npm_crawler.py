import urllib.request
import json
import string
import random
import sys


class NpmCrawler:

    # Constants
    API_URL = "http://registry.npmjs.org/"
    DEFAULT_DATA_FILE = "npm_data.json"
    DEFAULT_AVOID_FILE = "npm_data_avoid.json"
    DEFAULT_SAVE_INTERVAL = 50
    KEEP_KEYS = ["name", "author", "description",
                 "dependencies", "license",
                 "devDependencies"]

    # Member tracking variables
    data_file = ""
    avoid_file = ""
    pretty = False
    data = []
    avoid = set()
    found_packages = set()
    new_packages = set()

    def __init__(self,
                 data_file=DEFAULT_DATA_FILE,
                 avoid_file=DEFAULT_AVOID_FILE,
                 pretty=False):

        # Update member variables
        self.data_file = data_file
        self.avoid_file = avoid_file
        self.pretty = pretty

        # Initialize the object
        self.load_data_file()
        self.load_avoid_file()

    def load_data_file(self):
        """Loads an existing package data file in to memory"""

        try:
            with open(self.data_file, "r") as file:

                # Save data and update tracking variables
                self.data = json.load(file)
                self.found_packages = {p["name"] for p in self.data}
                [self.get_new_packages(p) for p in self.data]

        except FileNotFoundError:
            print("Error: No data file found, using blank data list instead.")

    def save_data(self):
        """Saves the current data in memory to the package data file"""

        with open(self.data_file, "w") as file:

            # Save JSON formatted if requested
            if self.pretty:
                json.dump(self.data, file, indent=4,
                          sort_keys=True, check_circular=False)
            else:
                json.dump(self.data, file, check_circular=False)

        print("Package data saved.")

    def load_avoid_file(self):
        """Loads an existing package avoid file in to memory"""

        try:
            with open(self.avoid_file, "r") as file:

                # Save data and update tracking variables
                self.avoid = set(json.load(file))

        except FileNotFoundError:
            print("Error: No avoid file found, using no initial avoids.")

    def save_avoid(self):
        """Saves the current avoid packages in memory to the avoid file"""

        with open(self.avoid_file, "w") as file:

            # Save JSON
            json.dump(list(self.avoid), file, check_circular=False)

        print("Packages to avoid saved.")

    def get_new_packages(self, data_object):
        """Parses out new package names from a package data object

        Parameters
        ----------
        data_object : package_object
            A package object to be parsed
        """

        # The keys in a package to search for
        keys = ["dependencies", "devDependencies"]

        # Append new packages from the data object
        for key in keys:
            if key in data_object:
                self.new_packages.update({p.split("/")[-1]
                                          for p in data_object[key]
                                          if p not in self.found_packages})

    def get_random_package(self, max_attempts=10):
        """Fetches a random package from NPM using a random search"""

        if max_attempts == 0:
            return

        try:  # Try to get package info
            url = urllib.request.urlopen(
                "http://registry.npmjs.org/-/v1/search?text=" +
                "".join(random.choice(string.ascii_lowercase + string.digits)
                        for n in range(3)))
        except urllib.error.HTTPError:
            return

        # Get npm data
        res_data = json.loads(url.read().decode("utf-8"))
        res_packages = res_data["objects"]

        if len(res_packages):
            package_name = random.choice(res_packages)["package"]["name"]

            if package_name not in self.found_packages:
                return package_name

        return self.get_random_package(max_attempts - 1)

    def get_package_data(self, package_name):
        """Gets package information from a given package name

        Parameters
        ----------
        package_name : string
            The NPM package name to fetch

        Returns
        -------
        A : bool
            Whether or not the fetch was sucessful
        """

        # Break if already added or should be skipped
        if package_name in self.found_packages or package_name in self.avoid:
            return False

        # Try to get package info
        try:
            url = urllib.request.urlopen(
                self.API_URL + package_name + "/latest")
        except urllib.error.HTTPError:
            self.avoid.add(package_name)
            print("Warning: Invalid package name `" + package_name + "`.")
            return False

        # Get npm data
        res_data = json.loads(url.read().decode("utf-8"))

        # Create new data object
        new_data = {
            key: res_data[key] for key in self.KEEP_KEYS if key in res_data
        }

        # Add to data list
        self.data.append(new_data)

        # Populate package tracking variables
        self.found_packages.add(package_name)
        self.get_new_packages(new_data)

        return True

    def gather_package_data(self,
                            start_package_name=None,
                            save_interval=DEFAULT_SAVE_INTERVAL,
                            auto_continue=True,
                            verbose=True):
        """Repeatedly searches for packages based on gathered info

        Parameters
        ----------
        start_package_name : string
            The name of the initial NPM package to search

        save_interval : int
            The number of packages to find between saves

        verbose : bool
            Whether or not to print the found package names

        auto_continue : bool
            Whether or not the search should continue on dependency exhaustion
        """

        # Initialize to random package name if none given
        if start_package_name is None:
            start_package_name = self.get_random_package()

        # Package count
        valid_found = 1

        while True:

            # Get initial package data
            self.get_package_data(start_package_name)

            # While there are still new packages to explore
            while len(self.new_packages):

                # Find the package data for an element in the set
                curr_package = self.new_packages.pop()
                added = self.get_package_data(curr_package)

                # Increment number found
                if added:
                    valid_found += 1

                # Provide feedback
                if added and verbose:
                    print("[" + str(len(self.found_packages)) +
                          " total] - found:", curr_package)

                # Save every SAVE_INTERVAL packages
                if save_interval > 0 and valid_found % save_interval == 0:
                    valid_found = 1
                    self.save_data()
                    self.save_avoid()

            # If we are only doing 1 search, break
            if not auto_continue:
                break

            # If told to auto-continue, recursively call with random package
            print("Found packages exhausted, searching for random package...")
            start_package_name = self.get_random_package()

            if start_package_name is None:
                print("Error: Unable to find random package in max attempts.")
                break
            else:
                print("Package `" + start_package_name +
                      "` found, continuing crawl.")

        # Save on completion
        self.save_data()
        self.save_avoid()

        print("Crawl completed.")


if __name__ == "__main__":

    # If no parameters, run default conditions
    if len(sys.argv) == 1:
        crawler = NpmCrawler()
        crawler.gather_package_data()
        sys.exit()

    # Catch missing parameters
    if len(sys.argv) < 6:
        print("usage: npm_crawler <data-file> <avoid-file> \
<start-package> <save-interval> <auto-continue>")
        sys.exit(-1)

    # Get command line params (no error checking, just gonna believe)
    data_file = sys.argv[1]
    avoid_file = sys.argv[2]
    start_package = sys.argv[3]
    save_interval = int(sys.argv[4])
    auto_continue = sys.argv[5] == "t"

    crawler = NpmCrawler(data_file, avoid_file)
    crawler.gather_package_data(start_package, save_interval)


"""
NPM Package object format /{package}/latest

{
    "name": "",
    "_id": ""
    "author": {
        "name": ""
    },
    "description": "",
    "dependencies": {
        "acorn": "^5.0.0",
        // ...
    },
    "license" : "", // Maybe good data?
    "devDependencies": {
        "acorn": "^5.0.0",
        // ...
    },
}
"""
