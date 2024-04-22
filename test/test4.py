import os

if __name__ == '__main__':
    f = "/home/model-server/tmp/tmp_vl5fofl/jsp-demo2/jsp-demo2/WEB-INF/classes/org/apache/jsp/welcome_jsp.java"

    i = f.find('/WEB-INF/classes/')
    if i != -1:
        f = f[i:].lstrip('/WEB-INF/classes/')
        print(f)
        f =f.split('.')[0]
        print(f)

