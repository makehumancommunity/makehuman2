#!/usr/bin/python3
"""
build a windows version (not yet finished)
"""

import json

class winBuilder():
    def __init__(self, path):
        self.conf = path

    def cleanexit(self, num, text):
        print (text)
        exit(num)

    def readJSON(self, path: str) -> dict:
        try:
            f = open(path, 'r', encoding='utf-8')
        except:
            self.cleanexit (1, "Cannot read JSON " + path)

        try:
            json_object = json.load(f)
        except json.JSONDecodeError as e:
            self.cleanexit (2, "JSON format error in " + path + " > " + str(e))

        return json_object

    def createPynsistCfg(self, text):
        with open(self.pynsistcfg, "w") as tfile:
            print(text, file=tfile)

    def evaluatePynsistCfg(self):
        json_object = self.readJSON(self.conf)

        if "pynsistfile" not in json_object:
            self.cleanexit(3, "Missing 'pynsistfile' in " + self.conf)
        self.pynsistcfg = json_object["pynsistfile"]

        if "mhconfigfile" not in json_object:
            self.cleanexit(3, "Missing 'mhconfigfile' in " + self.conf)

        mhconfig = json_object["mhconfigfile"]
        mhobject = self.readJSON(mhconfig)

        if "pynsist" not in json_object:
            self.cleanexit(4, "Missing 'pynsist' in " + self.conf)

        pynsist = json_object["pynsist"]

        outtext = ""
        for cat in "Application", "Python", "Include":
            if cat not in pynsist:
                self.cleanexit(3, "Missing " + cat + " in " + self.conf)

            outtext += "\n[" + cat + "]\n"
            if cat == "Application":
                appl = pynsist["Application"]
                for item in ("name", "version", "publisher", "script", "icon"):
                    if item not in appl:
                        self.cleanexit(4, "Missing " + item + " in " + cat)

                    if item == "name":
                        if "name" not in mhobject:
                            self.cleanexit(4, "Missing name in " + mhconfig)
                        outtext += "name=" + mhobject["name"] + "\n"

                    elif item == "version":
                        if "version" not in mhobject:
                            self.cleanexit(4, "Missing version in " + mhconfig)
                        outtext += "version=" + ".".join([str(num) for num in mhobject["version"]]) + "\n"

                    elif item == "publisher":
                        if "copyright" not in mhobject:
                            self.cleanexit(4, "Missing copyright in " + mhconfig)
                        outtext += "publisher=" + mhobject["copyright"] + "\n"

                    else:
                        outtext += item + "=" + appl[item] + "\n"

            elif cat == "Python":
                pyth = pynsist["Python"]
                for item in ("version", "bitness", "format"):
                    if item not in pyth:
                        self.cleanexit(4, "Missing " + item + " in " + cat)
                    outtext += item + "=" + str(pyth[item]) + "\n"

            elif cat == "Include":
                incl = pynsist["Include"]
                for item in ("packages", "pypi_wheels", "files"):
                    if item == "pypi_wheels":
                        outtext += "pypi_wheels= "
                        for elem in incl["pypi_wheels"]:
                            outtext += elem + "==" + incl["pypi_wheels"][elem] + "\n"
                    elif item == "files":
                        outtext += "\nfiles= "
                        for elem in incl["files"]:
                            outtext += elem + "\n"
        return outtext

if __name__ == '__main__':
    wb = winBuilder("./build.json")
    outtext = wb.evaluatePynsistCfg()
    wb.createPynsistCfg(outtext)

exit(0)
