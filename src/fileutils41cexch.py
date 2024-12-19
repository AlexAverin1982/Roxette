import os

def replace_strings_in_file(filename, replace_data: dict):
    with open(filename, 'r+', encoding='utf-8-sig') as myfile:
        text = myfile.read()
        for replace_what, replace_with in replace_data.items():
            text = text.replace(replace_what, replace_with)
        myfile.seek(0)
        myfile.write(text)
        myfile.truncate()

def remove_strings_in_file(filename, strings_to_remove: list):
    with open(filename, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    with open(filename, 'w', encoding='utf-8-sig') as f:
        for line in lines:
            if line.strip() not in strings_to_remove:
                f.write(line)

def merge_templates(file1, file2, priority:int = 0):
    if not os.path.exists(file1) or not os.path.isfile(file1): return
    if not os.path.exists(file2) or not os.path.isfile(file2): return
    if priority: file1, file2 = file2, file1


    with open(file1, 'r', encoding='utf-8-sig') as f1: lines1 = f1.readlines()
    with open(file2, 'r', encoding='utf-8-sig') as f2: lines2 = f2.readlines()

    search_end = False
    section_write = False

    for line in lines2:                 # просматриваем, что из второго файла не хватает в первом
        line = line.strip()
        if not line: continue
        if search_end:                  # проматываем текущую секцию до конца (она уже есть в первом файле)
            if line.endswith('_end='):  # конец секции отслеживаем
                search_end = False
            continue
        else:
            if section_write:           # идет дозапись секции из второго файла в первый
                lines1.append(line + '\n')
                if line.endswith('_end='): section_write = False    # записали секцию полностью, дальше снова анализируем, чего не хватает в первом файле
            elif line+'\n' in lines1:
                # проматываем до конца секции, она уже есть в первом файле
               search_end = True
            else:   # новая секция, которой нет в первом файле, начинаем писать
                section_write = True
                lines1.append('\n' + line + '\n')

    with open('merge_result' + os.path.splitext(file1)[1], 'w', encoding='utf-8-sig') as f:
        f.writelines(lines1)