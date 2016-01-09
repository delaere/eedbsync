<?php
ini_set('display_errors', 'On');
error_reporting(E_ALL | E_STRICT);
date_default_timezone_set( "Europe/Brussels" );

$servername = "localhost";
$username = "eedomus";
$password = "eedomus";
$dbname = "eedb";

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
} 
/* change character set to utf8 */
if (!$conn->set_charset("utf8")) {
    die("Error loading character set utf8: %s\n" . $conn->error);
}

/* fetch the devices */
function devices($conn) {
	$sql = "SELECT * FROM deviceview;";
	$result = $conn->query($sql);
	$results = array();
	if ($result->num_rows > 0) {
	    // output data of each row
	    while($row = $result->fetch_assoc()) {
		$results[] = array(
		   "periph_id" => $row["periph_id"],
		   "parent_periph_id" => $row["parent_periph_id"],
		   "name" => $row["name"],
		   "room_id" => $row["room_id"],
		   "room_name" => $row["room_name"],
		   "usage_id" => $row["usage_id"],
		   "usage_name" => $row["usage_name"],
		   "creation_date" => $row["creation_date"]
	        );
	    }
	echo json_encode($results);
	} else {
	    echo "0 results";
	}
}

function getValue($conn, $periph_id) {
	$sql = "SELECT measurement,timestamp FROM periph_history WHERE periph_id=" . $periph_id . " ORDER BY id DESC LIMIT 1;";
	$result = $conn->query($sql);
	$results = array();
	if ($result->num_rows > 0) {
		while($row = $result->fetch_assoc()) { 
			$results[] = array(
				"measurement" => $row["measurement"],
				"timestamp" => $row["timestamp"]
			);
		}
	}
	echo json_encode($results);
}

function getPeriphHistory($conn, $periph_id, $start_date = NULL ,$end_date = NULL) {
	if (is_null($end_date)) $end_date = date("Y-m-d H:i:s");
	if (is_null($start_date)) $start_date = date("Y-m-d H:i:s",strtotime("-1 year", time())); 
	$sql = "SELECT measurement,timestamp FROM periph_history WHERE periph_id=". $periph_id  ." AND timestamp between \"". $start_date ."\" and \"". $end_date ."\" ORDER BY timestamp DESC;";
	$result = $conn->query($sql);
	$results = array();
	if ($result->num_rows > 0) {
		while($row = $result->fetch_assoc()) {
			$results[] = array(
				"measurement" => $row["measurement"],
				"timestamp" => $row["timestamp"]
			);
		}
	}
	echo json_encode($results);
}

switch ($_GET["function"]) {
	case "history":
		getPeriphHistory($conn,$_GET["deviceID"],htmlspecialchars($_GET["start_date"]),htmlspecialchars($_GET["end_date"]));
		break;

	case "periphList":
		devices($conn);
		break;

	case "value";
		getValue($conn,$_GET["deviceID"]);
		break;
}
$conn->close();
?>
