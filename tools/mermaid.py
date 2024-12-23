from langchain_core.runnables.graph_mermaid import draw_mermaid_png

def save_mermaid_as_png(mermaid_code, output_file_path):
    # Draw the Mermaid graph and save it as PNG
    png_bytes = draw_mermaid_png(mermaid_syntax=mermaid_code, output_file_path=output_file_path)
    
    # Optionally, you can return the bytes if needed
    return png_bytes

if __name__ == "__main__":
    # Read Mermaid code from an external file
    with open('mer.txt', 'r') as file:
        mermaid_code = file.read()
    
    # Specify the output file path
    output_file = "mermaid_diagram.png"
    
    # Save the diagram as PNG
    save_mermaid_as_png(mermaid_code, output_file)
    
    print(f"Diagram saved as {output_file}")
