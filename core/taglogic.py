"""
    License information: data/licenses/makehuman_license.txt
    Author: black-punkduck

    Classes:
    * tagLogic
"""

class tagLogic():
    def __init__(self, json):
        self.reserved = ["Translate", "GuessName", "Shortcut"]
        self.tagreplace = {}
        self.tagfromname = {}
        self.fromnamesorted = []        # sorted keys for tagfromname by length
        self.tagproposals = []
        self.json = json

    def proposals(self):
        return self.tagproposals

    def convertJSON(self, json, separator=":", prepend = ""):
        """
        convert JSON to a list of proposals like 'slot:top-torso:layer3:jacket'

        :param dict json: json dictionary
        :param str separator: separactor for layers, usually ':'
        :param str prepend: string to be prepended
        """
        for key, item in json.items():
            if key in self.reserved:
                continue
            if type(item) is dict:
                self.convertJSON(item, separator, prepend + key + separator)
            elif type(item) is list:
                for l in item:
                    self.tagproposals.append((prepend + key + separator + l).lower())

    def createTagGroups(self, subtree, path):
        """
        create texts from selection filter (JSON), prepends path if available

        :param dict subtree: part or complete JSON dictionary of selection_filter
        :param str path: a path separated by ':' like :slot:bottom
        """
        for key, item in subtree.items():

            if isinstance(key, str):
                if key == "Translate":                             # extra, insert into tagreplace dictionary
                    for l in item:
                        self.tagreplace[l.lower()] = item[l]
                    continue

                if key == "GuessName":                             # extra, insert into tagfromname dictionary
                    for l in item:
                        self.tagfromname[l.lower()] = item[l]
                    continue

                if isinstance(item, dict):
                    self.createTagGroups(item, path + ":" + key.lower())    # next subtree

                elif isinstance(item, list):
                    if key == "Shortcut":
                        pass
                    else:
                        for l in item:                              # insert into tagreplace dictionary
                            repl = path + ":" + key.lower()
                            self.tagreplace[l.lower()] = repl[1:]       # get rid of first ":"

        if path == "":
            self.fromnamesorted = sorted(self.tagfromname, key=len, reverse=True)

    def completeTags(self, name, tags):
        """
        replace original tags if needed, append those not found or check name and create tag from that
        all done in lower case

        :param str name: name of asset
        :param list tags: tags to be tested
        :return: new tags
        """
        newtags = []
        for tag in tags:
            ltag = tag.lower()
            if ltag in self.tagreplace:             # in case it needs to be replaced
                elem = self.tagreplace[ltag]
                if elem is not None:
                    if elem.startswith("="):        # if replacement starts with '=' replace complete tag
                        ntag = elem[1:]
                    else:                           # else append tag
                        ntag = elem+":"+ltag
                    if ntag not in newtags:         # only append if new
                        newtags.append(ntag)
            else:
                if tag not in newtags:              # append tags not found and not yet available
                    newtags.append(tag)

        for tag in self.fromnamesorted:             # check for longest fitting name first (bathingsuit before suit)
            if tag in name:
                ntag = self.tagfromname[tag]
                if ntag not in newtags:             # append that tag and stop
                    newtags.append(ntag)
                    break

        return newtags

    def create(self):
        self.convertJSON(self.json)
        self.createTagGroups(self.json, "")
