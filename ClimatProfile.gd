class_name ClimateProfile
extends RefCounted

var average_temperature: float = 0.0
var average_moisture: float = 0.0
var average_height: float = 0.0
var rainfall: float = 0.0
var wind_strength: float = 0.0
var wind_direction: Vector2 = Vector2.RIGHT
var tectonic_activity: float = 0.0
var latitude: float = 0.0

func duplicate_profile() -> ClimateProfile:
	var c := ClimateProfile.new()
	c.average_temperature = average_temperature
	c.average_moisture = average_moisture
	c.average_height = average_height
	c.rainfall = rainfall
	c.wind_strength = wind_strength
	c.wind_direction = wind_direction
	c.tectonic_activity = tectonic_activity
	c.latitude = latitude
	return c

func to_dict() -> Dictionary:
	return {
		"average_temperature": average_temperature,
		"average_moisture": average_moisture,
		"average_height": average_height,
		"rainfall": rainfall,
		"wind_strength": wind_strength,
		"wind_direction": {"x": wind_direction.x, "y": wind_direction.y},
		"tectonic_activity": tectonic_activity,
		"latitude": latitude
	}

static func from_dict(data: Dictionary) -> ClimateProfile:
	var c := ClimateProfile.new()
	c.average_temperature = float(data.get("average_temperature", 0.0))
	c.average_moisture = float(data.get("average_moisture", 0.0))
	c.average_height = float(data.get("average_height", 0.0))
	c.rainfall = float(data.get("rainfall", 0.0))
	c.wind_strength = float(data.get("wind_strength", 0.0))
	var wd := data.get("wind_direction", {"x": 1.0, "y": 0.0})
	c.wind_direction = Vector2(float(wd.get("x", 1.0)), float(wd.get("y", 0.0)))
	c.tectonic_activity = float(data.get("tectonic_activity", 0.0))
	c.latitude = float(data.get("latitude", 0.0))
	return c