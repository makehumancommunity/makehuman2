#!/usr/bin/python3

import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Shorten BVH File.\n"
        "Program mostly reduces filesize by using shorter floats.\n"
        "It is also possible to reduce a file accidentally saved with bone-distances.\n"
        "Using a factor of 3 independent values the animation can be scaled individually.\n"
        "Additionally animation can be moved in height",
            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("filename", type=str, help="filename")
    parser.add_argument("-V", type=float, default=0.0, help="move character vertical in V units, -V -9")
    parser.add_argument("-f", type=float, default=1.0, nargs=3, help="Factor to scale root bone animation, example  -f 10 -10 10")
    parser.add_argument("-r", action="store_true", help="Reduce to rotation for all bones except for root.")

    args = parser.parse_args()

    cols = 0
    bone = 0
    delete = 0
    mask = []

    with open (args.filename, "r") as f:

        # first analyse structure
        #
        data = False
        while not data:
            line = f.readline().replace('\t', " ") # readability, but wrong for BVH
            if line == '':
                print ("File ended without frames")
                exit(22)


            pos = line.find("CHANNELS")
            if pos > -1:
                s = line[pos+9:]
                words = s.split()
                try:
                    num = int(words[0])
                    cols += num

                    if args.r:
                        if bone > 0 and num == 6:
                            delete += 3
                            submask = [True, True, True, True, True, True]
                            chan = words[1:]
                            for w in [ "Xposition", "Yposition", "Zposition"]:
                                if w in chan:
                                    submask[chan.index(w)] = False
                            mask.extend(submask)
                            text = " 3"
                            for c,l in enumerate(submask):
                                if l:
                                    text += (" " + chan[c])
                            print(line[:pos+9] + text)
                        else:
                            # bone zero
                            if num == 6:
                                mask.extend([True, True, True, True, True, True])
                            else:
                                mask.extend([True, True, True])
                            print(line, end='')
                    else:
                        print(line, end='')
                    bone += 1
                except Exception as e:
                    print (str(e))
                    pass
            else:
                print(line, end='')

            if line.startswith("MOTION") or line.startswith("Frame"):
                data = True

        """
        print (cols)
        print (delete)
        print (mask)
        """

        line = "dummy"
        while line != "":
            line = f.readline()
            if line == "":
                break
            words = line.split()
            try:
                float(words[0])
                text = ""
                for i, word in enumerate(words):
                    val = float(word)
                    if i < 3:
                        val *= args.f[i]
                    if i == 2:
                        val+= args.V
                    if mask[i]:
                        if val < 0.0001 and val > -0.0001:
                            text += " 0"
                        else:
                            text += " " + str(round(val,4))
                print (text[1:])
            except ValueError:
                print(line, end='')

        """
    corrected = False
    corrvalue = 0.0
    h = None
    if args.C:
        h = 0.0
    elif args.V != 0.0:
        h = args.V

    column = 0
    delete = 0
    #
    for line in f:
        # find number of columns to work with
        #
        new = line.replace('\t', " ") # readability, but wrong for BVH
        pos = line.find("CHANNELS")
        if pos > -1:
            s = line[pos+9:]
            words = s.split()
            try:
                num = int(words[0])
                cols += num
                if column > 1 and num > 3:
                    delete += (num - 3)
                column += 1
            except:
                pass
            print(new, end='')
            continue

        words = line.split()
        try:
            float(words[0])
            text = ""
            for i, word in enumerate(words):
                val = float(word)
                if i < 3:
                    val *= args.f[i]

                if i == 2:
                    if h is not None:
                        if corrected is False:
                            corrvalue = val - h
                            val = h
                            corrected = True
                        else:
                            val-= corrvalue

                if val < 0.0001 and val > -0.0001:
                    text += " 0"
                else:
                    text += " " + str(round(val,4))
            print (text[1:])
        except ValueError:
            print(new, end='')
        """
