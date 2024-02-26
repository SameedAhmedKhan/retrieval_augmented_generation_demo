# Retrieval-augmented generation (RAG)

A basic RAG project was done that utilizes Weaviate as a vector Database and Mistral models to give sensible answers to the queries.

# Usage

Clone the project and then run the project using the following command:

python main.py -query <your_query>

If you are running to program first time, it is recommended to add the data. A sample data is provided in menu.json.


## First time
python main.py -query <your_query> -data true

In first run, the program would load necessary models and might take time, however afterwards it processes really fast. The execution time depends on the processor mainly.