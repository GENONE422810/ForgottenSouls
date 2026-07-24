class_name CoastGenerator
extends RefCounted

static func get_coast_factor(
	chunk_coord: Vector2i,
	local_pos: Vector2i,
	deca: DecaChunkData,
	graph: WorldGraph = null
) -> float:
	var world_pos := chunk_coord * ChunkData.SIZE + local_pos
	var height := WorldSeed.height(Vector2(world_pos))
	var sea_level := _sea_level(deca)
	var edge := _edge_strength(local_pos)
	var ocean_pressure := 0.0

	if graph != null:
		ocean_pressure = graph.get_neighbor_ocean_pressure(deca.coord)

	var coastal := 0.0
	coastal += edge * 0.35
	coastal += ocean_pressure * 0.45
	coastal += clamp((sea_level - height + 0.08) * 3.0, 0.0, 0.45)

	if deca.climate.rainfall > 0.65 and height < sea_level + 0.10:
		coastal += 0.08

	return clamp(coastal, 0.0, 1.0)

static func is_coastal_tile(
	chunk_coord: Vector2i,
	local_pos: Vector2i,
	deca: DecaChunkData,
	graph: WorldGraph = null
) -> bool:
	return get_coast_factor(chunk_coord, local_pos, deca, graph) > 0.55

static func _sea_level(deca: DecaChunkData) -> float:
	return -0.05 + deca.climate.rainfall * 0.02 - deca.climate.average_height * 0.02

static func _edge_strength(local_pos: Vector2i) -> float:
	var edge_dist := min(
		min(local_pos.x, ChunkData.SIZE - 1 - local_pos.x),
		min(local_pos.y, ChunkData.SIZE - 1 - local_pos.y)
	)
	return 1.0 - clamp(float(edge_dist) / 4.0, 0.0, 1.0)