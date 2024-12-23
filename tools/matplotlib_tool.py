import subprocess
import os
import sys

def execute_script_and_save_image(script_name, output_image_name):
    # Use the current Python executable
    python_executable = sys.executable
    
    # Execute the external Python script
    try:
        subprocess.run([python_executable, script_name], check=True)
        print("Script executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error executing script: {e}")
        print(f"Return code: {e.returncode}")
        return  # Exit if there's an error

    # Define the directory where charts will be saved
    charts_directory = 'charts'
    
    # Create the directory if it doesn't exist
    if not os.path.exists(charts_directory):
        os.makedirs(charts_directory)
        print(f"Created directory: {charts_directory}")

    # Check if the temporary output file exists
    temp_output_file = 'temp_output.png'
    
    if os.path.exists(temp_output_file):
        # Define the full path for the output image
        output_image_path = os.path.join(charts_directory, output_image_name)
        
        # Rename the temporary output file to the desired output image name
        os.rename(temp_output_file, output_image_path)
        print(f"Chart saved as {output_image_path}")
    else:
        print("Error: Temporary output file not found.")

if __name__ == "__main__":
    # Specify the name of the script and desired output image name
    script_to_run = 'test_matplot.py'  # Name of your external script
    output_image_name = 'final_chart.png'  # Desired name for the output image
    
    # Execute the script and save the result
    execute_script_and_save_image(script_to_run, output_image_name)
