import os
import re

def read_file(file_path):
    """Read content of a file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def write_file(file_path, content):
    """Write content to a file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def extract_packages(content):
    """Extract usepackage commands from content."""
    packages = re.findall(r'\\usepackage(?:\[.*?\])?\{.*?\}', content)
    return packages

def remove_document_tags(content):
    """Remove \begin{document} and \end{document} tags."""
    content = re.sub(r'\\begin\{document\}\s*', '', content)
    content = re.sub(r'\\end\{document\}\s*', '', content)
    return content

def remove_latex_markers(content):
    """Remove ```latex markers from content."""
    # Remove ```latex at the start of the content
    content = re.sub(r'^```latex\s*', '', content)
    # Remove ```latex anywhere in the content
    content = re.sub(r'\n```latex\s*', '\n', content)
    # Remove closing ``` markers
    content = re.sub(r'\n```\s*', '\n', content)
    return content

def process_files(input_dir):
    # File order
    file_order = [
        'abstract_intro.md',
        'background.md',
        'related_works_with_charts.md',
        'research_methodes_with_charts.md',
        'review_findings_with_charts.md',
        'discussion_conclusion.md'
    ]
    
    # Read abstract_intro first
    abstract_intro_path = os.path.join(input_dir, 'abstract_intro.md')
    abstract_intro_content = read_file(abstract_intro_path)
    
    # Remove latex markers from abstract_intro
    abstract_intro_content = remove_latex_markers(abstract_intro_content)
    
    # Get existing packages in abstract_intro
    existing_packages = extract_packages(abstract_intro_content)
    new_packages = []
    
    # Process all files except abstract_intro
    for filename in os.listdir(input_dir):
        if filename.endswith('.md') and filename != 'abstract_intro.md':
            file_path = os.path.join(input_dir, filename)
            content = read_file(file_path)
            
            # Remove latex markers
            content = remove_latex_markers(content)
            
            # Extract and compare packages
            file_packages = extract_packages(content)
            for package in file_packages:
                if package not in existing_packages and package not in new_packages:
                    new_packages.append(package)
                    # Remove package from original file
                    content = content.replace(package + '\n', '')
                    content = content.replace(package, '')
            
            # Remove document tags
            content = remove_document_tags(content)
            
            # Write modified content back
            write_file(file_path, content)
    
    # Insert new packages into abstract_intro
    if new_packages:
        # Find the last usepackage command
        last_package_pos = abstract_intro_content.rfind('\\usepackage')
        if last_package_pos != -1:
            # Find the end of the last package command
            end_pos = abstract_intro_content.find('}', last_package_pos) + 1
            # Insert new packages after the last existing package
            modified_content = (abstract_intro_content[:end_pos] + '\n' + 
                              '\n'.join(new_packages) + 
                              abstract_intro_content[end_pos:])
        else:
            # If no existing packages, add at the beginning
            modified_content = '\n'.join(new_packages) + '\n' + abstract_intro_content
    else:
        modified_content = abstract_intro_content
    
    # Remove only \end{document} from abstract_intro
    modified_content = modified_content.replace('\\end{document}', '')
    write_file(abstract_intro_path, modified_content)
    
    # Ensure discussion_conclusion ends with \end{document}
    discussion_path = os.path.join(input_dir, 'discussion_conclusion.md')
    if os.path.exists(discussion_path):
        discussion_content = read_file(discussion_path)
        if '\\end{document}' not in discussion_content:
            discussion_content = discussion_content.rstrip() + '\n\\end{document}\n'
            write_file(discussion_path, discussion_content)
    
    # Create combined results files
    combined_content = ''
    for filename in file_order:
        if os.path.exists(os.path.join(input_dir, filename)):
            content = read_file(os.path.join(input_dir, filename))
            combined_content += content + '\n\n'
    
    # Write combined content to both .md and .tex files
    write_file('results.md', combined_content)
    write_file('results.tex', combined_content)

if __name__ == '__main__':
    # Specify the input directory containing the MD files
    input_directory = 'Results'
    process_files(input_directory)
    print("Processing completed successfully!")