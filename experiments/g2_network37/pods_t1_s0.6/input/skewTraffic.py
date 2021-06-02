import os
traffic_file = open( "traffic.conf", 'r')
list_lines = traffic_file.readlines()

for i,line in enumerate(list_lines):
    if line.startswith('#'):
        continue
    newline = line.strip().split(',')
    for j in range(len(newline)):
        newline[j] = newline[j].strip()
    
    src = int(newline[1][1:])
    dst = int(newline[2][1:])
    if (src-1)//4 != (dst-1)//4:
        newline[3] = str(int(newline[3])//2)
    
    newlinestr = ''
    for element in newline:
        newlinestr += element
        newlinestr += ', '
    newlinestr = newlinestr[:-2]
    newlinestr += '\n'
    list_lines[i] = newlinestr
    
new_content = ''
for line in list_lines:
    new_content += line
new_content = new_content[:-1]

with open( "new_traffic.conf", 'w') as gc:
    gc.write(new_content)