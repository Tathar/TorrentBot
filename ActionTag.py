#!/usr/bin/env python3

# from pyppeteer.page import Page as pypage
from pyppeteer import errors


class ActionTag:
    def __init__(self,
                 selector,
                 data=None,
                 action="Auto",
                 error=True,
                 timeout=30000):
        self.selector = selector
        self.data = data
        self.action = action
        self.error = bool(error)
        self.options = {"timeout": timeout, "visible": True}
        self.timeout = timeout
        if self.action == "Auto":
            if self.data is not None:
                self.action = "field"
            else:
                self.action = "button"

        if self.action not in ("field", "button", "wait", "hover", "clear"):
            raise NotImplementedError()

    async def run(self, page):
        print("wait " + self.selector, "for", self.options["timeout"])
        try:
            await page.waitForSelector(self.selector, self.options)  # timeout
            if self.action != "wait":
                selector = await page.querySelector(self.selector)
                if self.action == "button":
                    await selector.click()
                elif self.action == "field":
                    await selector.type(self.data)
                    # for key in self.data:
                    #     await selector.press(key)
                elif self.action == "clear":
                    await selector.click()
                    await page.keyboard.down("Control")
                    await page.keyboard.press('KeyA')
                    await page.keyboard.up("Control")
                    await page.keyboard.press('Backspace')

                elif self.action == "hover":
                    await selector.hover()
        except errors.TimeoutError:
            if self.error == True:
                raise

    def __str__(self) -> str:
        return "ActionTag[" + str(self.selector) + ", " + str(
            self.data) + ", " + str(self.error) + ", " + str(
                self.timeout) + "]"

    def __repr__(self) -> str:
        return "ActionTag[" + str(self.selector) + ", " + str(
            self.data) + ", " + str(self.error) + ", " + str(
                self.timeout) + "]"
