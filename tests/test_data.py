import pandas.api.types as ptypes
import pytest

from app.data import EmissionData, GenerationMixData


@pytest.fixture(scope="module")
def emission_data():
    return EmissionData.build()


def test_emission_data_has_proper_type(emission_data: EmissionData) -> None:
    assert set(emission_data.df_history.Type) == {"Målt"}
    assert set(emission_data.df_forecast.Type) == {"Prognose"}


def test_emission_data_has_some_data(emission_data: EmissionData) -> None:
    assert len(emission_data.df_history) == 576
    # Data has five minute resolution so let's check that there's more than 12 points
    # of history and forecast to ensure that we have at least an hour worth of data.
    assert len(emission_data.df_forecast) > 12


def test_emission_data_has_positive_co2_values(emission_data: EmissionData) -> None:
    assert (emission_data.df_history.CO2Emission > 0).all()
    assert (emission_data.df_forecast.CO2Emission > 0).all()


def test_emission_data_has_expected_columns(emission_data: EmissionData) -> None:
    expected = {"CO2Emission", "Minutes5DK", "Minutes5UTC", "Type"}
    assert set(emission_data.df_history.columns) == expected
    assert set(emission_data.df_forecast.columns) == expected


def test_emission_data_times_have_expected_type(emission_data: EmissionData) -> None:
    assert ptypes.is_datetime64_any_dtype(emission_data.df_history.Minutes5UTC)
    assert ptypes.is_datetime64_any_dtype(emission_data.df_forecast.Minutes5UTC)
    assert ptypes.is_datetime64_any_dtype(emission_data.df_history.Minutes5DK)
    assert ptypes.is_datetime64_any_dtype(emission_data.df_forecast.Minutes5DK)


@pytest.fixture(scope="module")
def generation_mix_data():
    return GenerationMixData.build()


def test_generation_mix_data_has_two_zones(
    generation_mix_data: GenerationMixData,
) -> None:
    assert len(generation_mix_data.df_mix) == 2


def test_generation_mix_data_has_expected_columns(
    generation_mix_data: GenerationMixData,
) -> None:
    expected = {
        "Biomass",
        "ExchangeContinent",
        "ExchangeGreatBelt",
        "ExchangeNordicCountries",
        "FossilGas",
        "FossilHardCoal",
        "FossilOil",
        "HourDK",
        "HourUTC",
        "HydroPower",
        "OffshoreWindPower",
        "OnshoreWindPower",
        "OtherRenewable",
        "PriceArea",
        "SolarPower",
        "TotalLoad",
        "Waste",
    }
    assert set(generation_mix_data.df_mix.columns) <= expected
