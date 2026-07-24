class_name WorldGraph
extends RefCounted

const NEIGHBOR_OFFSETS := [
	Vector2i(-1, -1), Vector2i(0, -1), Vector2i(1, -1),
	Vector2i(-1, 0),                     Vector2i(1, 0),
	Vector2i(-1, 1),  Vector2i(0, 1),  Vector2i(1, 1)
]

var deca_chunks: Dictionary = {} # Vector2i -> DecaChunkData

func clear() -> void:
	deca_chunks.clear()

func set_deca(coord: Vector2i, deca: DecaChunkData) -> void:
	deca_chunks[coord] = deca

func has_deca(coord: Vector2i) -> bool:
	return deca_chunks.has(coord)

func get_deca(coord: Vector2i) -> DecaChunkData:
	return deca_chunks.get(coord, null)

func get_neighbor_decas(coord: Vector2i) -> Array:
	var out: Array = []
	for off in NEIGHBOR_OFFSETS:
		var d: DecaChunkData = get_deca(coord + off)
		if d != null:
			out.append(d)
	return out

func get_neighbor_ocean_pressure(coord: Vector2i) -> float:
	var pressure := 0.0
	var count := 0

	for off in NEIGHBOR_OFFSETS:
		var d: DecaChunkData = get_deca(coord + off)
		if d == null:
			continue
		count += 1
		if d.is_ocean:
			pressure += 1.0
		elif d.climate.rainfall > 0.72:
			pressure += 0.25

	if count == 0:
		return 0.0

	return clamp(pressure / float(count), 0.0, 1.0)

func get_neighbor_average_profile(coord: Vector2i) -> ClimateProfile:
	var total := ClimateProfile.new()
	var count := 0

	for off in NEIGHBOR_OFFSETS:
		var d: DecaChunkData = get_deca(coord + off)
		if d == null or d.climate == null:
			continue

		total.average_temperature += d.climate.average_temperature
		total.average_moisture += d.climate.average_moisture
		total.average_height += d.climate.average_height
		total.rainfall += d.climate.rainfall
		total.wind_strength += d.climate.wind_strength
		total.tectonic_activity += d.climate.tectonic_activity
		total.latitude += d.climate.latitude
		total.wind_direction += d.climate.wind_direction
		count += 1

	if count == 0:
		return null

	total.average_temperature /= count
	total.average_moisture /= count
	total.average_height /= count
	total.rainfall /= count
	total.wind_strength /= count
	total.tectonic_activity /= count
	total.latitude /= count

	if total.wind_direction.length() > 0.001:
		total.wind_direction = total.wind_direction.normalized()
	else:
		total.wind_direction = Vector2.RIGHT

	return total

func get_neighbor_terrain_bias(coord: Vector2i) -> Dictionary:
	var bias: Dictionary = {}

	for off in NEIGHBOR_OFFSETS:
		var d: DecaChunkData = get_deca(coord + off)
		if d == null:
			continue
		bias[d.terrain] = int(bias.get(d.terrain, 0)) + 1

	return bias