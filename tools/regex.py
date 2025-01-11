import os
import re

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def write_file(file_path, content):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def extract_latex_commands(content):
    packages = re.findall(r'\\usepackage(?:\[.*?\])?\{.*?\}', content)
    doc_class = re.findall(r'\\documentclass(?:\[.*?\])?\{.*?\}', content)
    return packages, doc_class

def remove_latex_markers(content):
    content = re.sub(r'^```latex\s*', '', content, flags=re.MULTILINE) # MULTILINE flag
    content = re.sub(r'\n```latex\s*', '\n', content)
    content = re.sub(r'\n```\s*', '\n', content)
    return content

def remove_document_tags(content):
    content = re.sub(r'\\begin\{document\}\s*', '', content)
    content = re.sub(r'\\end\{document\}\s*', '', content)
    content = re.sub(r'\\documentclass(?:\[.*?\])?\{.*?\}\s*', '', content) # Improved regex
    content = re.sub(r'\\bibliography\{.*?\}\s*', '', content)
    content = re.sub(r'\\section\*\{Abstract\}\s*', '', content) # Remove Abstract Section*
    return content

def remove_package_commands(content, packages, whitelist=None):
    if whitelist is None:
        whitelist = []  # Initialize to empty list if None
    for package in packages:
        if package not in whitelist: # Only remove if not in whitelist
            content = content.replace(package + '\n', '')
            content = content.replace(package, '')
    return content

def process_files(input_dir):
    file_order = [
        'abstract_intro.md', 'background.md', 'related_works_with_charts.md',
        'research_methodes_with_charts.md', 'review_findings_with_charts.md',
        'discussion_conclusion.md'
    ]

    all_packages = set()
    doc_class = None
    package_whitelist = [
        r'\\usepackage\{graphicx\}',
        r'\\usepackage\{tikz\}',
        r'\\usepackage\{pgfplots\}',
        r'\\usepackage\{pgf-pie\}',
        r'\\usepackage\{smartdiagram\}',
        r'\\usepackage\{longtable\}',
        r'\\usepackage\{lscape\}',
        r'\\usepackage\{multirow\}',
        r'\\usepackage\{tabularx\}',
        r'\\usepackage\{threeparttable\}',
        r'\\usepackage\{float\}',
        r'\\usepackage\{url\}',
        r'\\usepackage\{hyperref\}',
        r'\\usepackage\{colortbl\}',
        r'\\usepackage\{booktabs\}',
        r'\\usepackage\{array\}',
        r'\\usepackage\{enumitem\}',
        r'\\usepackage\{cite\}',
        r'\\usepackage\{amsmath\}',
        r'\\usepackage\{amssymb\}',
        r'\\usepackage\{amsfonts\}'
    ]

    for filename in os.listdir(input_dir):
        if filename.endswith('.md'):
            file_path = os.path.join(input_dir, filename)
            content = read_file(file_path)
            content = remove_latex_markers(content)

            packages, doc_classes = extract_latex_commands(content)
            all_packages.update(packages)

            if not doc_class and doc_classes:
                doc_class = doc_classes[0]

    if not doc_class:
        doc_class = r'\documentclass[a4paper,11pt]{article}'

    combined_content = f"{doc_class}\n\n"
    combined_content += '\n'.join(sorted(all_packages)) + '\n\n'
    combined_content += '\\begin{document}\n\n'

    for filename in file_order:
        file_path = os.path.join(input_dir, filename)
        if os.path.exists(file_path):
            content = read_file(file_path)
            content = remove_latex_markers(content)
            content = remove_document_tags(content)
            content = remove_package_commands(content, all_packages, package_whitelist)

            content = re.sub(r'\n\s*\n', '\n\n', content.strip()) # Improved whitespace removal
            combined_content += content + '\n\n'

    combined_content += '\\bibliography{biblio}\n'
    combined_content += '\\end{document}\n'

    combined_content = re.sub(r'\n\s*\n', '\n\n', combined_content) #Final whitespace removal
    write_file('results.md', combined_content)
    write_file('results.tex', combined_content)

if __name__ == '__main__':
    input_directory = 'Results'
    process_files(input_directory)
    print("Processing completed successfully!")