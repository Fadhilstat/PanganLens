import pytest

from panganlens.validation.mapping import (
    CanonicalMapping,
    EntityType,
    MappingRegistry,
    SourceMappingKey,
)


def test_mapping_registry_resolves_reviewed_source_id_exactly():
    registry = MappingRegistry(
        (
            CanonicalMapping(
                key=SourceMappingKey(
                    entity_type=EntityType.COMMODITY,
                    source_system="PIHPS",
                    source_id="com_3",
                    source_name="Beras",
                ),
                canonical_id="commodity_beras",
            ),
        )
    )

    mapping = registry.require(
        SourceMappingKey(
            entity_type=EntityType.COMMODITY,
            source_system="pihps",
            source_id="COM_3",
            source_name="  BERAS  ",
        )
    )

    assert mapping.canonical_id == "commodity_beras"


def test_region_mapping_can_include_parent_context():
    registry = MappingRegistry(
        (
            CanonicalMapping(
                key=SourceMappingKey(
                    entity_type=EntityType.REGION,
                    source_system="pihps",
                    source_name="Kota Bandung",
                    source_level="regency",
                    parent_source_id="12",
                ),
                canonical_id="region_kota_bandung",
            ),
        )
    )

    assert (
        registry.require(
            SourceMappingKey(
                entity_type=EntityType.REGION,
                source_system="PIHPS",
                source_name="Kota Bandung",
                source_level="regency",
                parent_source_id="12",
            )
        ).canonical_id
        == "region_kota_bandung"
    )


def test_unknown_mapping_fails_closed():
    registry = MappingRegistry(())

    with pytest.raises(KeyError, match="not mapped"):
        registry.require(
            SourceMappingKey(
                entity_type=EntityType.REGION,
                source_system="pihps",
                source_name="Unknown Region",
                source_level="province",
            )
        )


def test_duplicate_source_mapping_is_rejected():
    key = SourceMappingKey(
        entity_type=EntityType.CHANNEL,
        source_system="pihps",
        source_id="1",
    )

    with pytest.raises(ValueError, match="duplicate source mapping key"):
        MappingRegistry(
            (
                CanonicalMapping(key=key, canonical_id="channel_a"),
                CanonicalMapping(key=key, canonical_id="channel_b"),
            )
        )


def test_mapping_key_requires_source_identity():
    with pytest.raises(ValueError, match="source_id or source_name"):
        SourceMappingKey(
            entity_type=EntityType.MARKET,
            source_system="pihps",
        ).normalized()
