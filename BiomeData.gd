class_name BiomeData
extends RefCounted

enum Biome{
	OCEAN,
	BEACH,

	PLAINS,
	FOREST,
	DENSE_FOREST,

	SWAMP,

	DESERT,

	SAVANNA,

	STEPPE,

	TAIGA,

	SNOW,

	MOUNTAIN,

	HIGH_MOUNTAIN,

	RIVER
}

static func get_tile(biome:int)->int:

	match biome:

		Biome.OCEAN:
			return 0

		Biome.BEACH:
			return 1

		Biome.PLAINS:
			return 2

		Biome.FOREST:
			return 3

		Biome.DENSE_FOREST:
			return 4

		Biome.DESERT:
			return 5

		Biome.SWAMP:
			return 6

		Biome.SAVANNA:
			return 7

		Biome.STEPPE:
			return 8

		Biome.TAIGA:
			return 9

		Biome.SNOW:
			return 10

		Biome.MOUNTAIN:
			return 11

		Biome.HIGH_MOUNTAIN:
			return 12

		Biome.RIVER:
			return 13

	return 2