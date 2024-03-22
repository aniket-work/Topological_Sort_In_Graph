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

        # Execute topological sort algorithm and calculate distance from source
        result = session.run(query_topological_sort)

        # Store the results in a list
        result_list = list(result)

        # Print sorted sequence of courses with maxDistanceFromSource
        print("Topological Sort Order:")
        for record in result_list:
            course = record['course']
            print(f"Course: {course}, Max Distance from Source: {record['maxDistanceFromSource']}")

        # Create a Network object
        network = Network(notebook=False)

        # Add nodes and keep track of added nodes
        added_nodes = set()
        for record in result_list:
            print("in result for loop")
            course = record['course']
            if not course:
                print("Empty course name found in record:", record)
            else:
                course_lower = course.lower()  # Convert to lowercase
                if course not in added_nodes:  # Check if node already added
                    network.add_node(course_lower)  # Add node to the graph
                    added_nodes.add(course_lower)  # Update set of added nodes
                    print("Added node:", course_lower)  # Debug print
                else:
                    print("Course already added:", course_lower)
            print("Current added nodes:", added_nodes)  # Print current set of added nodes

        # Add edges based on relationships in the graph
        query_get_edges = """
        MATCH (source)-[:PREREQUISITE]->(target)
        RETURN source.name AS source, target.name AS target
        """
        edges = session.run(query_get_edges)
        for edge in edges:
            source = edge['source'].lower()  # Convert to lowercase
            target = edge['target'].lower()  # Convert to lowercase

            if source in added_nodes and target in added_nodes:  # Check if both nodes exist
                network.add_edge(source, target)  # Add edge to the graph
                print(f"Adding edge: {source} -> {target}")  # Debug print
            else:
                print(f"Ignoring edge: {source} -> {target}")  # Debug print

        # Print out nodes and edges data for debugging
        print("Nodes:", network.get_nodes())
        print("Edges:", network.get_edges())

        # Save the graph to an HTML file
        graph_html_file = 'sorted_courses_graph.html'
        network.save_graph(graph_html_file)
        print(f"Sorted courses graph exported to '{graph_html_file}'")

        print(f"Graph exported to '{graph_html_file}'")

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
