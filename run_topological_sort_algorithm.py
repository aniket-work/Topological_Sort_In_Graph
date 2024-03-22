import networkx as nx
from neo4j import GraphDatabase
from pyvis.network import Network
import webbrowser

# Neo4j connection parameters
uri = "bolt://localhost:7687"
user = "neo4j"
password = "abcd1234"


# Function to create dummy course data using NetworkX
def create_dummy_course_data():
    G = nx.DiGraph()
    courses = {
        "Calculus": [],
        "Linear Algebra": ["Calculus"],
        "Intro to Programming": [],
        "Data Structures": ["Intro to Programming"],
        "Algorithms": ["Data Structures"],
        "Database Systems": ["Data Structures"],
        "Web Development": ["Database Systems"],
        "Machine Learning": ["Linear Algebra"],
        "Advanced Algorithms": ["Algorithms"],
        "Operating Systems": ["Algorithms"]
    }
    for course, prereqs in courses.items():
        for prereq in prereqs:
            G.add_edge(prereq, course)
    return G


# Function to convert NetworkX graph to Neo4j
def networkx_to_neo4j(graph, driver):
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        for node in graph.nodes:
            session.run("CREATE (:Course {name: $name})", name=node)
        for edge in graph.edges:
            session.run("""
            MATCH (c1:Course {name: $course1}), (c2:Course {name: $course2})
            CREATE (c1)-[:PREREQUISITE]->(c2)
            """, course1=edge[0], course2=edge[1])


# Function to run topological sort algorithm using GDS
def run_topological_sort():
    # Connect to Neo4j
    driver = GraphDatabase.driver(uri, auth=(user, password))

    # Cypher query to project the graph for topological sorting
    query_project_graph = """
    CALL gds.graph.project(
      'courseGraph', 
      'Course',
      {
        PREREQUISITE: {
          type: 'PREREQUISITE',
          orientation: 'NATURAL'
        }
      }
    )
    """

    # Cypher query to run topological sort algorithm and calculate distance from source
    query_topological_sort = """
    CALL gds.dag.topologicalSort.stream(
      'courseGraph',
      {
        relationshipTypes: ['PREREQUISITE'], 
        computeMaxDistanceFromSource: true
      }
    )
    YIELD nodeId, maxDistanceFromSource
    WITH nodeId, maxDistanceFromSource
    MATCH (course:Course) WHERE id(course) = nodeId
    RETURN course.name AS course, maxDistanceFromSource
    """

    with driver.session() as session:
        # Delete any existing projected graph
        session.run("CALL gds.graph.drop('courseGraph', false)")

        # Create the graph for topological sorting
        session.run(query_project_graph)

        # Execute topological sort algorithm
        result = session.run(query_topological_sort)

        # Print sorted sequence of courses with maxDistanceFromSource
        print("Topological Sort Order:")
        sorted_courses = []
        for record in result:
            course = record['course']
            sorted_courses.append(course)
            print(f"Course: {course}, Max Distance from Source: {record['maxDistanceFromSource']}")

        # Create a Network object
        network = Network(notebook=False)
        network.add_nodes(sorted_courses)

        # Add edges
        for i in range(len(sorted_courses) - 1):
            network.add_edge(sorted_courses[i], sorted_courses[i + 1])

        # Save the graph to an HTML file
        graph_html_file = 'sorted_courses_graph.html'
        network.save_graph(graph_html_file)
        print(f"Sorted courses graph exported to '{graph_html_file}'")

        # Open the HTML file in a web browser
        webbrowser.open_new_tab(graph_html_file)


# Main function
def main():
    # Create dummy course data using NetworkX
    G = create_dummy_course_data()

    # Connect to Neo4j and convert course data
    driver = GraphDatabase.driver(uri, auth=(user, password))
    networkx_to_neo4j(G, driver)

    # Run topological sort algorithm
    run_topological_sort()


if __name__ == "__main__":
    main()
