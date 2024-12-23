# script_to_run.py
import matplotlib.pyplot as plt

def generate_chart():
    # Sample data
    x = [1, 2, 3, 4, 5]
    y = [2, 3, 5, 7, 11]

    # Create a line chart
    plt.plot(x, y)
    plt.title('Line Chart from External Script')
    plt.xlabel('X-axis')
    plt.ylabel('Y-axis')

    # Save the chart as PNG (this will be overridden)
    plt.savefig('temp_output.png')
    plt.close()  # Close the figure to free up memory

if __name__ == "__main__":
    generate_chart()
