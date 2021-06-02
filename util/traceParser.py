"""
G2_RIGHTS.

Module to parse traffic configuration file.

"""

class TraceParser:
    """Class definition for traffic config file parsing.

    Args:
        path (str): Path to input traffic config file.

    Attributes:
        jobs (list): List of jobs obtained from traffic config file. Each job corresponds to a single flow
        specified in the file, and represented as a Python dictionary.

    """

    def __init__(self, path):
        fileContent = None
        try:
            with open(path) as f:
                fileContent = f.readlines()
        except IOError as e:
            print("TraceParser: Couldn't open file ({}).".format(e))
        self.jobs = []
        if fileContent:
            for line in fileContent:
                line = line.strip()
                if line and not line.strip().startswith('#'):
                    tokens = line.split(',')
                    if len(tokens) < 7:
                        info("**** [G2]: traffic.conf should at least specify job id, source host, destination host, bytes to transfer, time to start the transfer, expected fair share, specified path; exiting...\n")
                        return                       
                    j = {
                        'id': int(tokens[0].strip()),
                        'src': tokens[1].strip(),
                        'dst': tokens[2].strip(),
                        'size': float(tokens[3].strip()),
                        'time': float(tokens[4].strip()),
                        'share': float(tokens[5].strip()),
                        'traversedNodes': tokens[6].strip().split(' '),
                        'dscp': 'N/A',
                        'bitrate': 'N/A',
                        'transport': 'TCP'
                        }        
                    if len(tokens) > 7:
                            j['dscp'] = tokens[7].strip()
                            j['bitrate'] = tokens[8].strip()
                            j['transport'] = tokens[9].strip()
                    self.jobs.append(j)
        # Check whether the IDs are valid.
        if self.jobs:
            idList = [j['id'] for j in self.jobs]
            if (min(idList) != 1) or (not sorted(idList) == list(range(min(idList), max(idList)+1))):
                self.jobs = []
                print("TraceParser: invalid IDs in traffic configuration.")
        if not self.jobs:
            print("TraceParser: returned empty traffic configuration.")
