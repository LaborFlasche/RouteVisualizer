# Use the official Python slim image as the base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY src/requirements.txt /app/src/

# Install the required Python packages
RUN pip install --no-cache-dir -r src/requirements.txt

# Copy the application code into the container
COPY src/ /app/src/
COPY images/ /app/images/
COPY .streamlit/ /app/.streamlit/
COPY addresses.txt /app/


# Set PYTHONPATH so Python can find the src module
ENV PYTHONPATH=/app

# Expose the default Streamlit port
EXPOSE 8501


# Command to run the Streamlit app
CMD ["streamlit", "run", "src/main_start.py", "--server.port=8501", "--server.address=0.0.0.0"]