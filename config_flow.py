import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from .const import DOMAIN, DEFAULT_HOST

class UIProtoRadioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for UIProto Radio."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step when user adds the integration via UI."""
        errors = {}
        if user_input is not None:
            # Erstelle den Eintrag mit der eingegebenen IP
            return self.async_create_entry(
                title="Internetradio", data=user_input
            )

        schema = vol.Schema({
            vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )