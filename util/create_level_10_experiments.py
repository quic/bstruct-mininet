import os
import json


def generate_shortest_paths():
    """
    Generates the string version of shortest_paths file
    Note all "\n"'s are not necessary, they are just for ease of display
    """
    names = []
    for host in range(1, 13):
        for name in ["s" + str(host), "h" + str(host)]:
            names.append(name)

    shortest_paths = "{\n"
    for src in names:
        shortest_paths += '\"' + src + "\": {\n"
        for dst in names:
            if int(src[1:]) == int(dst[1:]):
                shortest_paths += '\"' + dst + "\": [\n"

                shortest_paths += '\"' + src + "\""
                if dst != src:
                    shortest_paths += ",\n"
                    shortest_paths += '\"' + dst + "\""

                shortest_paths += "\n]"
                if dst != names[-1]:
                    shortest_paths += ",\n"
            elif int(src[1:]) < int(dst[1:]):
                shortest_paths += '\"' + dst + "\": [\n"

                shortest_paths += '\"' + src + "\",\n"
                if src[0] == 'h':
                    shortest_paths += '\"s' + src[1:] + "\",\n"

                for idx in range(int(src[1:]) + 1, int(dst[1:])):
                    shortest_paths += '\"s' + str(idx) + "\",\n"

                shortest_paths += '\"s' + dst[1:] + "\""
                if dst[0] == 'h':
                    shortest_paths += ",\n"
                    shortest_paths += '\"' + dst + "\""

                shortest_paths += "\n]"
                if dst != names[-1]:
                    shortest_paths += ",\n"
        shortest_paths += "\n}"
        if src != names[-1]:
            shortest_paths += ",\n"
    shortest_paths += "\n}"

    return shortest_paths


def make_shortest_paths_file(path_dir):
    """
    Accepts path_dir as the path of the directory to save shortest_paths file, and saves a json file to this directory
    """
    shortest_paths_obj = json.loads(generate_shortest_paths())
    with open(os.path.join(path_dir, "shortest_paths.json"), "w") as f:
        json.dump(shortest_paths_obj, f)
        f.close()


def make_g2_conf_file(path_dir, tcp_cc: str):
    """
    It is based on an existing g2.conf file. It replaces tcp congestion control, and saves to a given directory.
    :param path_dir: the path of directory to save g2_conf file
    :param tcp_cc: the desired tcp congestion control algorithm
    """
    f = open("./files/g2.conf")
    g2_conf_string = str()

    flag = False
    for line in f:
        if flag:
            line = "tcp_congestion_control: " + tcp_cc + "\n"
            flag = False
        g2_conf_string += line
        if line == "# TCP congestion control mechanism to use for iperf test.\n":
            flag = True

    f_write = open(os.path.join(path_dir, "g2.conf"), "w")
    f_write.write(g2_conf_string)
    f_write.close()
    f.close()


def make_traffic_conf_file(path_dir, level, n_dup):
    """
    This function creates the traffic of certain level, duplicates them, and saves to certain file. The default traffic
    volume = 256MB, starting time = 0.0
    :param path_dir: the path of the directory to save g2_conf file
    :param level: which level
    :param n_dup: number of duplications
    """
    F_switches_all = {1: [1, 2, 3], 2: [2, 3, 4], 3: [3, 4, 5], 4: [4, 5, 6], 5: [5, 6, 7], 6: [6, 7, 8],
                      7: [7, 8, 9], 8: [8, 9, 10], 9: [9, 10, 11], 10: [10, 11, 12]}
    F = {key: F_switches_all[key] for key in range(1, level + 1)}
    header = "# Format: int job id, source host, destination host, number of bytes to transfer, time in seconds to start the transfer, expected fair share of the flow in Mbits/sec\n"
    traffic_conf_string = header

    counter = 0
    for f in F.values():
        src = f[0]
        dst = f[-1]
        line = ", h" + str(src) + ", h" + str(dst) + ", 256000000, 0, 0.0\n"
        for _ in range(n_dup):
            counter += 1
            new_line = str(counter) + line
            traffic_conf_string += new_line

    f_write = open(os.path.join(path_dir, "traffic.conf"), "w")
    f_write.write(traffic_conf_string)
    f_write.close()


def make_dir(tcp_cc: str, level: int, n_dup: int):
    """
    Takes tcp congestion control, level and number of duplications as inputs, creates a folder with "input" and "output"
    subdirectories. The input subdirectory has g2.conf and traffic.conf files, and output subdirectory has
    shortest_paths.json file.
    Note that only files in input subdirectory change; shortest_paths.json remains the same.
    """
    path = "./10_level_exp/" + tcp_cc + '_' + "level" + str(level) + '_' + "dup" + str(n_dup)
    if not os.path.isdir(path):
        os.makedirs(path)

    input_path = os.path.join(path, "input")
    if not os.path.isdir(input_path):
        os.mkdir(input_path)
    make_g2_conf_file(input_path, tcp_cc)
    make_traffic_conf_file(input_path, level, n_dup)

    output_path = os.path.join(path, "output")
    if not os.path.isdir(output_path):
        os.mkdir(output_path)
    make_shortest_paths_file(output_path)

# Test
# for tcp_cc in ["bbr", "cubic"]:
#     for level in range(1, 11):
#         for n_dup in range(1, 6):
#             make_dir(tcp_cc=tcp_cc, level=level, n_dup=n_dup)
