"""
Тести валідації каталогу
Запускати з кореня проекту: pytest tests/

Ці тести гарантують, що:
1. Усі виробники проходять валідацію Pydantic
2. Критичні поля заповнені (address_consumption для I/O модулів!)
3. Внутрішня консистентність (max_total_devices vs loops × per_loop)
4. JSON-серіалізація і десеріалізація працює
5. Очікувані виробники присутні в каталозі
"""
import json

import pytest
from pydantic import ValidationError

from schemas.catalog import (
    Catalog, DataStatus, IOModuleType, Manufacturer, Panel, PanelType,
    PricingStatus,
)
from catalog.cofem import COFEM
from catalog.tiras import TIRAS
from catalog.omega import OMEGA
from catalog.varta import VARTA
from catalog.placeholders import (
    APOLLO, ARTON, BOSCH, ESSER, HOCHIKI, SCHRACK, SIEMENS,
)
from build_catalog import CATALOG


class TestCatalogIntegrity:
    """Перевіряє, що каталог зібраний правильно"""
    
    def test_catalog_has_11_manufacturers(self):
        assert len(CATALOG.manufacturers) == 11
    
    def test_all_expected_manufacturers_present(self):
        expected_ids = {
            "tiras", "omega", "varta", "cofem",
            "bosch", "siemens", "hochiki", "apollo",
            "esser", "schrack", "arton",
        }
        actual_ids = {m.manufacturer_id for m in CATALOG.manufacturers}
        assert expected_ids == actual_ids
    
    def test_manufacturer_ids_unique(self):
        ids = [m.manufacturer_id for m in CATALOG.manufacturers]
        assert len(ids) == len(set(ids))
    
    def test_3_ua_manufacturers_complete(self):
        complete = CATALOG.manufacturers_by_status(DataStatus.COMPLETE)
        complete_ids = {m.manufacturer_id for m in complete}
        # Tiras, Омега, Варта — наші основні UA-бренди, мають complete-дані
        assert {"tiras", "omega", "varta"}.issubset(complete_ids)
    
    def test_arton_is_starter(self):
        assert ARTON.data_status == DataStatus.STARTER
    
    def test_european_brands_preliminary(self):
        # Європейські — preliminary до уточнення цін через дистриб'юторів
        for mfr_id in ["bosch", "siemens", "hochiki", "apollo", "esser", "schrack"]:
            mfr = CATALOG.get_by_id(mfr_id)
            assert mfr.data_status == DataStatus.PRELIMINARY, (
                f"{mfr_id} має data_status = {mfr.data_status}, очікувалось PRELIMINARY"
            )


class TestCriticalFields:
    """Перевіряє наявність критичних полів"""
    
    @pytest.mark.parametrize("mfr_id", ["cofem", "tiras", "omega"])
    def test_io_modules_have_address_consumption(self, mfr_id):
        """address_consumption — критичне поле для розрахунку архітектурного податку"""
        mfr = CATALOG.get_by_id(mfr_id)
        for module in mfr.io_modules:
            assert module.address_consumption >= 1, (
                f"{mfr_id}/{module.module_id}: address_consumption має бути ≥1"
            )
    
    def test_cofem_io_modules_are_1_address(self):
        """Cofem унікальний тим, що його I/O займають 1 адресу. Це треба зафіксувати."""
        for module in COFEM.io_modules:
            if module.module_id in ("cofem_mstay8", "cofem_mstay", "cofem_mda2ylt"):
                assert module.address_consumption == 1, (
                    f"{module.model_name}: Cofem MSTAY/MDA модулі мають займати 1 адресу"
                )
    
    def test_omega_io_modules_are_4_addresses(self):
        """Омега БСА/БКА займають 4 адреси — це підстава для архітектурного податку."""
        for module in OMEGA.io_modules:
            if module.module_id in ("omega_bsa", "omega_bka_220", "omega_brvu"):
                assert module.address_consumption == 4, (
                    f"{module.model_name}: Омега БСА/БКА/БРВУ мають займати 4 адреси"
                )


class TestPanelConsistency:
    """Перевіряє внутрішню консистентність панелей"""
    
    def test_panel_total_devices_within_capacity(self):
        """max_total_devices не може перевищувати loops × per_loop"""
        for mfr in CATALOG.manufacturers:
            for panel in mfr.panels:
                theoretical_max = panel.max_loops * panel.devices_per_loop
                assert panel.max_total_devices <= theoretical_max, (
                    f"{mfr.manufacturer_id}/{panel.panel_id}: "
                    f"max_total_devices ({panel.max_total_devices}) перевищує "
                    f"max_loops × devices_per_loop ({theoretical_max})"
                )
    
    def test_panels_have_compatible_ids(self):
        """Якщо детектор/модуль вказує compatible_panel_ids, ці id мають існувати"""
        for mfr in CATALOG.manufacturers:
            panel_ids = {p.panel_id for p in mfr.panels}
            
            for detector in mfr.detectors:
                for pid in detector.compatible_panel_ids:
                    assert pid in panel_ids, (
                        f"{mfr.manufacturer_id}/{detector.detector_id}: "
                        f"compatible_panel_id '{pid}' не знайдено"
                    )
            
            for module in mfr.io_modules:
                for pid in module.compatible_panel_ids:
                    assert pid in panel_ids, (
                        f"{mfr.manufacturer_id}/{module.module_id}: "
                        f"compatible_panel_id '{pid}' не знайдено"
                    )


class TestSerialization:
    """Перевіряє, що каталог можна серіалізувати в JSON і назад"""
    
    def test_catalog_serializes_to_json(self):
        json_str = CATALOG.model_dump_json()
        data = json.loads(json_str)
        assert "manufacturers" in data
        assert len(data["manufacturers"]) == 11
    
    def test_catalog_round_trip(self):
        """Каталог можна зберегти і завантажити, дані не змінюються"""
        json_str = CATALOG.model_dump_json()
        reloaded = Catalog.model_validate_json(json_str)
        
        assert len(reloaded.manufacturers) == len(CATALOG.manufacturers)
        
        # Перевіряємо, що зберігся address_consumption у Cofem модулів
        cofem_reloaded = reloaded.get_by_id("cofem")
        mstay8_original = next(m for m in COFEM.io_modules if m.module_id == "cofem_mstay8")
        mstay8_reloaded = next(m for m in cofem_reloaded.io_modules if m.module_id == "cofem_mstay8")
        assert mstay8_original.address_consumption == mstay8_reloaded.address_consumption


class TestSchemaValidation:
    """Перевіряє, що схема ловить помилки"""
    
    def test_invalid_io_module_inputs_outputs_mismatch(self):
        """Output модуль не може мати входи"""
        from schemas.catalog import IOModule
        
        with pytest.raises(ValidationError):
            IOModule(
                module_id="test",
                model_name="Test",
                module_type=IOModuleType.OUTPUT,
                inputs_count=2,  # помилка: output не має входів
                outputs_count=1,
                address_consumption=1,
            )
    
    def test_invalid_panel_total_exceeds_capacity(self):
        """max_total_devices не може перевищувати теоретичний максимум"""
        with pytest.raises(ValidationError):
            Panel(
                panel_id="test",
                model_name="Test",
                panel_type=PanelType.COMPACT,
                max_loops=1,
                devices_per_loop=100,
                max_total_devices=200,  # помилка: 200 > 1×100=100
            )
    
    def test_invalid_address_consumption_zero(self):
        """address_consumption має бути ≥1"""
        from schemas.catalog import IOModule
        
        with pytest.raises(ValidationError):
            IOModule(
                module_id="test",
                model_name="Test",
                module_type=IOModuleType.INPUT,
                inputs_count=4,
                address_consumption=0,  # помилка
            )


class TestCompletenessTracking:
    """Перевіряє, що звіт повноти точний"""
    
    def test_overall_completeness_counts(self):
        report = CATALOG.overall_completeness()
        assert report["total_manufacturers"] == 11
        # Після уточнення EU-сертифікації UA-брендів (partial → none) їх дані
        # вважаються повнішими: Cofem приєднується до complete-групи.
        assert report["complete"] == 4  # Tiras, Омега, Варта, Cofem
        assert report["preliminary"] == 6  # 6 EU брендів
        assert report["starter"] == 1  # Артон
        assert report["ready_for_mvp"] == 10  # все крім Артон
    
    def test_arton_completeness_report(self):
        """Артон має бути позначений як стартовий з мінімумом даних"""
        report = ARTON.completeness_report()
        assert report["data_status"] == DataStatus.STARTER
        assert report["panels_count"] == 0  # поки нема даних
