import allure
from pwpf.core.base_page import BasePage

from apps.uitesting_playground.locators.dynamic_id_page_locators import DynamicIdPageLocators


class DynamicIdPage(BasePage):
    @allure.step("Click the dynamic-id button")
    def click_button(self) -> None:
        self.click_role_button(DynamicIdPageLocators.BUTTON)
