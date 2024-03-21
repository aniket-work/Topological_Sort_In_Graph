import random
from neo4j import GraphDatabase
from pyvis.network import Network

# Function to generate a complex corporate routing network
def generate_routing_network(num_routers, max_connections_per_router):
    routers = [f'Router{i}' for i in range(num_routers)]
    connections = []

    for source_router in routers:
        num_connections = random.randint(1, max_connections_per_router)
        target_routers = random.sample([r for r in routers if r != source_router], num_connections)
        for target_router in target_routers:
            connections.append((source_router, target_router))

    return routers, connections

def generate_random_routing_path(routers):
    random.shuffle(routers)
    return routers

# Function to load data into Neo4j
def load_data_into_neo4j(tx, routers, connections):
    for router in routers:
        tx.run("CREATE (:Router {id: $id})", id=router)

    for source, target in connections:
        tx.run("MATCH (a:Router {id: $source}), (b:Router {id: $target}) "
               "CREATE (a)-[:CONNECTED_TO]->(b)",
               source=source, target=target)

# Function to project the graph into the GDS library
def project_graph(tx):
    tx.run("CALL gds.graph.project("
           "  'routing_graph',"
           "  'Router',"
           "  { CONNECTED_TO: { orientation: 'UNDIRECTED' } },"
           "  { }"
           ")").value()[0]
    graph_name = "routing_graph"
    print("Projected graph name:", graph_name)
    return graph_name

# Function to run the topological sort algori101thm
def run_topological_sort(tx, graph_name):
    query = (
        "CALL gds.dag.topologicalSort.stream($graph_name, {computeMaxDistanceFromSource: true})"
        "YIELD nodeId, maxDistanceFromSource "
        "RETURN gds.util.asNode(nodeId).id AS router, maxDistanceFromSource "
        "ORDER BY maxDistanceFromSource, router"
    )
    result = tx.run(query, graph_name=graph_name)
    return result

import webbrowser

import webbrowser

# Function to visualize the routing network
import webbrowser

def visualize_routing_network(routers, connections, topological_sort_result):
    net = Network(notebook=False, height='800px', width='100%', cdn_resources="remote")
    net.add_nodes(routers)
    for source, target in connections:
        net.add_edge(source, target)

    # Color the nodes based on the topological order
    colors = {
        0: 'green',  # Source routers
        1: 'blue',
        2: 'orange',
        3: 'red',
        4: 'purple',
        5: 'yellow'  # Routers with the highest distance from source
    }

    # Color nodes based on the topological sort result
    for node in net.nodes:
        distance = next((record['maxDistanceFromSource'] for record in topological_sort_result if record['router'] == node['id']), None)
        if distance is not None:
            node['color'] = colors.get(distance, 'gray')  # Use gray for higher distances

    # Generate a random routing path
    random_routing_path = generate_random_routing_path(routers)

    # Add the topological sort and random routing paths to the visualization
    topo_sort_path_id = 'Topological Sort Path'
    random_path_id = 'Random Path'
    net.add_node(topo_sort_path_id, shape='box', label='Topological Sort Path', color='green')
    net.add_node(random_path_id, shape='box', label='Random Path', color='red')
    for i, router in enumerate(topological_sort_result):
        net.add_edge(topo_sort_path_id, router['router'], label=f"Step {i+1}")
    for i, router in enumerate(random_routing_path):
        net.add_edge(random_path_id, router, label=f"Step {i+1}")

    # Use the barnes_hut layout algorithm for a static layout
    net.barnes_hut()

    # Save the network visualization to an HTML file
    html_file = 'routing_network.html'
    net.save_graph(html_file)
    print(f"Graph exported to '{html_file}'")

    # Open the HTML file in a web browser
    webbrowser.open_new_tab(html_file)

# Neo4j connection parameters
uri = "bolt://localhost:7687"
user = "neo4j"
password = "abcd1234"

# Connect to Neo4j
driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session() as session:
    # Generate a complex corporate routing network
    num_routers = 50  # Increase the number of routers for a more complex network
    max_connections_per_router = 10  # Increase the maximum number of connections per router
    routers, connections = generate_routing_network(num_routers, max_connections_per_router)

    # Load data into Neo4j
    session.execute_write(load_data_into_neo4j, routers, connections)

    # Delete any existing projected graph
    session.run("CALL gds.graph.drop('routing_graph', false)")

    # Project the graph into the GDS library
    graph_name = project_graph(session)

    # Run the topological sort algorithm
    topological_sort_result = run_topological_sort(session, graph_name)

    # Visualize the routing network
    visualize_routing_network(routers, connections, topological_sort_result)

# Close the Neo4j driver
driver.close()