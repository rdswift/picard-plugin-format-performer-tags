# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Bob Swift (rdswift)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.


import re

from picard.plugin3.api import (
    Metadata,
    OptionsPage,
    PluginApi,
    t_,
)

from .ui_options_format_performer_tags import Ui_FormatPerformerTagsOptionsPage


USER_GUIDE_URL = 'https://picard-plugins-user-guides.readthedocs.io/en/latest/format_performer_tags/user_guide.html'

performers_split = re.compile(r", | and ").split

WORD_LIST = ['guest', 'solo', 'additional']


class ManifestTranslations:
    NAME = t_("manifest.name", "Format Performer Tags")
    DESC = t_("manifest.description", "This plugin provides options with respect to the formatting of performer tags.")
    LONG = t_(
        "manifest.long_description",
        (
            "This plugin provides options with respect to the formatting of performer tags. The format of "
            "the resulting tags is controlled by the settings in the options page."
        )
    )


class FormatPerformerTags:
    def __init__(self, api: PluginApi):
        self.api = api

    def get_word_dict(self, settings):
        word_dict = {}
        for word in WORD_LIST:
            word_dict[word] = settings["format_group_" + word]
        return word_dict

    def rewrite_tag(self, key, values, metadata, word_dict, settings):
        if ':' not in key:
            mainkey = key
            subkey = ''
        else:
            mainkey, subkey = key.split(':', 1)
        self.api.logger.debug("%s: Removing key: '%s'", "Format Performer Tags", key,)
        metadata.delete(key)
        self.api.logger.debug("%s: Formatting Performer [%s: %s]", "Format Performer Tags", subkey, values,)
        if not subkey:
            instruments = []
        else:
            instruments = performers_split(subkey)
        if instruments:
            for instrument in instruments:
                groups = {1: [], 2: [], 3: [], 4: [],}
                vocals = ''
                if instrument:
                    instrument_key = ''
                    words = instrument.split()
                    for word in words[:]:
                        if word in WORD_LIST:
                            groups[word_dict[word]].append(word)
                            words.remove(word)
                    display_group = {}
                    for group_number in range(1, 5):
                        if groups[group_number]:
                            group_separator = settings["format_group_{0}_sep_char".format(group_number)]
                            if not group_separator:
                                group_separator = " "
                            display_group[group_number] = settings["format_group_{0}_start_char".format(group_number)] \
                                + group_separator.join(groups[group_number]) \
                                + settings["format_group_{0}_end_char".format(group_number)]
                        else:
                            display_group[group_number] = ""
                    if words:
                        instrument_key = ' '.join(words)
                        if (len(words) > 1) and (words[-1] in ["vocal", "vocals",]):
                            vocals = " ".join(words[:-1])
                            instrument_key = words[-1]
                    else:
                        instrument_key = ''
                    if vocals:
                        group_number = settings["format_group_vocals"]
                        temp_group = groups[group_number][:]
                        if group_number < 2:
                            temp_group.append(vocals)
                        else:
                            temp_group.insert(0, vocals)
                        group_separator = settings["format_group_{0}_sep_char".format(group_number)]
                        if not group_separator:
                            group_separator = " "
                        display_group[group_number] = settings["format_group_{0}_start_char".format(group_number)] \
                            + group_separator.join(temp_group) \
                            + settings["format_group_{0}_end_char".format(group_number)]
                newkey = ('%s:%s%s%s%s' % (mainkey, display_group[1], instrument_key, display_group[2], display_group[3],))
                self.api.logger.debug("%s: newkey: %s", "Format Performer Tags", newkey,)
                for value in values:
                    metadata.add_unique(newkey, (value + display_group[4]))
        else:
            newkey = '%s:' % (mainkey,)
            self.api.logger.debug("%s: newkey: %s", "Format Performer Tags", newkey,)
            for value in values:
                metadata.add_unique(newkey, value)

    def format_performer_tags(self, api, album, metadata, *args):
        word_dict = self.get_word_dict(self.api.plugin_config)
        for key, values in list(
            filter(lambda filter_tuple: filter_tuple[0].startswith('performer') or filter_tuple[0].startswith('~performersort'), metadata.rawitems())
        ):
            self.rewrite_tag(key, values, metadata, word_dict, self.api.plugin_config)


class FormatPerformerTagsOptionsPage(OptionsPage):

    TITLE = t_("ui.options_page_title", "Format Performer Tags")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.ui = Ui_FormatPerformerTagsOptionsPage()
        self.ui.setupUi(self)

        self._add_translations()
        self._add_connections()

        self.processor = FormatPerformerTags(self.api)

    def _add_translations(self):

        start_bold = '<span style="font-weight:600;">'
        end_bold = '</span>'

        blank = self.api.tr("ui.blank", "(blank)")
        keyword = self.api.tr("ui.keyword", "Keyword: {word}")

        self.setWindowTitle("Form")
        self.ui.gb_description.setTitle(self.api.tr("ui.gb_description", "Format Performer Tags"))
        self.ui.format_description.setText(
            "<html><head/><body><p>"
            + self.api.tr(
                "ui.format_description_p1",
                (
                    "These settings will determine the format for any {start_bold}Performer{end_bold} "
                    "tags prepared. The format is divided into six parts: the performer; the instrument or vocals; and four user "
                    "selectable sections for the extra information. This is set out as:"
                )
            ).format(start_bold=start_bold, end_bold=end_bold)
            + "</p><p align=\"center\">"
            + self.api.tr(
                "ui.format_description_p2",
                "{start_bold}[1]{end_bold}Instrument/Vocals{start_bold}[2][3]{end_bold}: Performer{start_bold}[4]{end_bold}"
            ).format(start_bold=start_bold, end_bold=end_bold)
            + "</p><p>"
            + self.api.tr(
                "ui.format_description_p3",
                "You can select the section in which each of the extra information words appears."
            )
            + "</p><p>"
            + self.api.tr(
                "ui.format_description_p4",
                (
                    "For each of the sections you can select the starting characters, the characters separating entries, and the ending "
                    "characters. Note that leading or trailing spaces must be included in the settings and will not be automatically added. "
                    "If no separator characters are entered, the items within a section will be automatically separated by a single space."
                )
            )
            + "</p><p>"
            + self.api.tr(
                "ui.format_description_p5",
                "Please see the {start_link}User Guide{end_link} for additional information."
            ).format(start_link=f'<a href="{USER_GUIDE_URL}"><span style="text-decoration: underline; color:#0000ff;">', end_link="</span></a>")
            + "</p></body></html>"
        )
        self.ui.gb_word_groups.setTitle(self.api.tr("ui.gb_word_groups", "Keyword Sections Assignment"))
        self.ui.group_additonal.setTitle(keyword.format(word="additional"))
        self.ui.additional_rb_1.setText("1")
        self.ui.additional_rb_2.setText("2")
        self.ui.additional_rb_3.setText("3")
        self.ui.additional_rb_4.setText("4")
        self.ui.group_guest.setTitle(keyword.format(word="guest"))
        self.ui.guest_rb_1.setText("1")
        self.ui.guest_rb_2.setText("2")
        self.ui.guest_rb_3.setText("3")
        self.ui.guest_rb_4.setText("4")
        self.ui.group_solo.setTitle(keyword.format(word="solo"))
        self.ui.solo_rb_1.setText("1")
        self.ui.solo_rb_2.setText("2")
        self.ui.solo_rb_3.setText("3")
        self.ui.solo_rb_4.setText("4")
        self.ui.group_vocals.setTitle(self.api.tr("ui.group_vocals", "All vocal type keywords"))
        self.ui.vocals_rb_1.setText("1")
        self.ui.vocals_rb_2.setText("2")
        self.ui.vocals_rb_3.setText("3")
        self.ui.vocals_rb_4.setText("4")
        self.ui.gb_group_settings.setTitle(self.api.tr("ui.gb_group_settings", "Section Display Settings"))
        self.ui.label_1.setText(self.api.tr("ui.label_1", "Section 1"))
        self.ui.label_2.setText(self.api.tr("ui.label_2", "Section 2"))
        self.ui.label_3.setText(self.api.tr("ui.label_3", "Section 3"))
        self.ui.label_4.setText(self.api.tr("ui.label_4", "Section 4"))
        self.ui.format_group_1_start_char.setPlaceholderText(blank)
        self.ui.format_group_1_sep_char.setPlaceholderText(blank)
        self.ui.format_group_1_end_char.setText(self.api.tr("ui.format_group_1_end_char", " "))
        self.ui.format_group_1_end_char.setPlaceholderText(blank)
        self.ui.label_5.setText(self.api.tr("ui.label_5", "Start Chars"))
        self.ui.label_6.setText(self.api.tr("ui.label_6", "Sep Chars"))
        self.ui.label_7.setText(self.api.tr("ui.label_7", "End Chars"))
        self.ui.format_group_2_start_char.setText(self.api.tr("ui.format_group_2_start_char", ", "))
        self.ui.format_group_2_start_char.setPlaceholderText(blank)
        self.ui.format_group_3_start_char.setText(self.api.tr("ui.format_group_3_start_char", " ("))
        self.ui.format_group_3_start_char.setPlaceholderText(blank)
        self.ui.format_group_4_start_char.setText(self.api.tr("ui.format_group_4_start_char", " ("))
        self.ui.format_group_4_start_char.setPlaceholderText(blank)
        self.ui.format_group_2_sep_char.setPlaceholderText(blank)
        self.ui.format_group_3_sep_char.setPlaceholderText(blank)
        self.ui.format_group_4_sep_char.setPlaceholderText(blank)
        self.ui.format_group_2_end_char.setPlaceholderText(blank)
        self.ui.format_group_3_end_char.setText(self.api.tr("ui.format_group_3_end_char", ")"))
        self.ui.format_group_3_end_char.setPlaceholderText(blank)
        self.ui.format_group_4_end_char.setText(self.api.tr("ui.format_group_4_end_char", ")"))
        self.ui.format_group_4_end_char.setPlaceholderText(blank)
        self.ui.gb_examples.setTitle(self.api.tr("ui.gb_examples", "Examples"))

    def _add_connections(self):
        self.ui.additional_rb_1.clicked.connect(self.update_examples)
        self.ui.additional_rb_2.clicked.connect(self.update_examples)
        self.ui.additional_rb_3.clicked.connect(self.update_examples)
        self.ui.additional_rb_4.clicked.connect(self.update_examples)
        self.ui.guest_rb_1.clicked.connect(self.update_examples)
        self.ui.guest_rb_2.clicked.connect(self.update_examples)
        self.ui.guest_rb_3.clicked.connect(self.update_examples)
        self.ui.guest_rb_4.clicked.connect(self.update_examples)
        self.ui.solo_rb_1.clicked.connect(self.update_examples)
        self.ui.solo_rb_2.clicked.connect(self.update_examples)
        self.ui.solo_rb_3.clicked.connect(self.update_examples)
        self.ui.solo_rb_4.clicked.connect(self.update_examples)
        self.ui.vocals_rb_1.clicked.connect(self.update_examples)
        self.ui.vocals_rb_2.clicked.connect(self.update_examples)
        self.ui.vocals_rb_3.clicked.connect(self.update_examples)
        self.ui.vocals_rb_4.clicked.connect(self.update_examples)
        self.ui.format_group_1_start_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_2_start_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_3_start_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_4_start_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_1_sep_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_2_sep_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_3_sep_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_4_sep_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_1_end_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_2_end_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_3_end_char.editingFinished.connect(self.update_examples)
        self.ui.format_group_4_end_char.editingFinished.connect(self.update_examples)

    def load(self):
        # Enable external link
        self.ui.format_description.setOpenExternalLinks(True)

        # Settings for Keyword: additional
        temp = self.api.plugin_config["format_group_additional"]
        if temp > 3:
            self.ui.additional_rb_4.setChecked(True)
        elif temp > 2:
            self.ui.additional_rb_3.setChecked(True)
        elif temp > 1:
            self.ui.additional_rb_2.setChecked(True)
        else:
            self.ui.additional_rb_1.setChecked(True)

        # Settings for Keyword: guest
        temp = self.api.plugin_config["format_group_guest"]
        if temp > 3:
            self.ui.guest_rb_4.setChecked(True)
        elif temp > 2:
            self.ui.guest_rb_3.setChecked(True)
        elif temp > 1:
            self.ui.guest_rb_2.setChecked(True)
        else:
            self.ui.guest_rb_1.setChecked(True)

        # Settings for Keyword: solo
        temp = self.api.plugin_config["format_group_solo"]
        if temp > 3:
            self.ui.solo_rb_4.setChecked(True)
        elif temp > 2:
            self.ui.solo_rb_3.setChecked(True)
        elif temp > 1:
            self.ui.solo_rb_2.setChecked(True)
        else:
            self.ui.solo_rb_1.setChecked(True)

        # Settings for all vocal keywords
        temp = self.api.plugin_config["format_group_vocals"]
        if temp > 3:
            self.ui.vocals_rb_4.setChecked(True)
        elif temp > 2:
            self.ui.vocals_rb_3.setChecked(True)
        elif temp > 1:
            self.ui.vocals_rb_2.setChecked(True)
        else:
            self.ui.vocals_rb_1.setChecked(True)

        # Settings for word group 1
        self.ui.format_group_1_start_char.setText(self.api.plugin_config["format_group_1_start_char"])
        self.ui.format_group_1_end_char.setText(self.api.plugin_config["format_group_1_end_char"])
        self.ui.format_group_1_sep_char.setText(self.api.plugin_config["format_group_1_sep_char"])

        # Settings for word group 2
        self.ui.format_group_2_start_char.setText(self.api.plugin_config["format_group_2_start_char"])
        self.ui.format_group_2_end_char.setText(self.api.plugin_config["format_group_2_end_char"])
        self.ui.format_group_2_sep_char.setText(self.api.plugin_config["format_group_2_sep_char"])

        # Settings for word group 3
        self.ui.format_group_3_start_char.setText(self.api.plugin_config["format_group_3_start_char"])
        self.ui.format_group_3_end_char.setText(self.api.plugin_config["format_group_3_end_char"])
        self.ui.format_group_3_sep_char.setText(self.api.plugin_config["format_group_3_sep_char"])

        # Settings for word group 4
        self.ui.format_group_4_start_char.setText(self.api.plugin_config["format_group_4_start_char"])
        self.ui.format_group_4_end_char.setText(self.api.plugin_config["format_group_4_end_char"])
        self.ui.format_group_4_sep_char.setText(self.api.plugin_config["format_group_4_sep_char"])

        self.update_examples()

    def save(self):
        self._set_settings(self.api.plugin_config)

    def restore_defaults(self):
        super().restore_defaults()
        self.update_examples()

    def _set_settings(self, settings):

        # Process 'additional' keyword settings
        temp = 2 if self.ui.additional_rb_2.isChecked() else 1
        temp = 3 if self.ui.additional_rb_3.isChecked() else temp
        temp = 4 if self.ui.additional_rb_4.isChecked() else temp
        settings["format_group_additional"] = temp

        # Process 'guest' keyword settings
        temp = 2 if self.ui.guest_rb_2.isChecked() else 1
        temp = 3 if self.ui.guest_rb_3.isChecked() else temp
        temp = 4 if self.ui.guest_rb_4.isChecked() else temp
        settings["format_group_guest"] = temp

        # Process 'solo' keyword settings
        temp = 2 if self.ui.solo_rb_2.isChecked() else 1
        temp = 3 if self.ui.solo_rb_3.isChecked() else temp
        temp = 4 if self.ui.solo_rb_4.isChecked() else temp
        settings["format_group_solo"] = temp

        # Process all vocal keyword settings
        temp = 2 if self.ui.vocals_rb_2.isChecked() else 1
        temp = 3 if self.ui.vocals_rb_3.isChecked() else temp
        temp = 4 if self.ui.vocals_rb_4.isChecked() else temp
        settings["format_group_vocals"] = temp

        # Settings for word group 1
        settings["format_group_1_start_char"] = self.ui.format_group_1_start_char.text()
        settings["format_group_1_end_char"] = self.ui.format_group_1_end_char.text()
        settings["format_group_1_sep_char"] = self.ui.format_group_1_sep_char.text()

        # Settings for word group 2
        settings["format_group_2_start_char"] = self.ui.format_group_2_start_char.text()
        settings["format_group_2_end_char"] = self.ui.format_group_2_end_char.text()
        settings["format_group_2_sep_char"] = self.ui.format_group_2_sep_char.text()

        # Settings for word group 3
        settings["format_group_3_start_char"] = self.ui.format_group_3_start_char.text()
        settings["format_group_3_end_char"] = self.ui.format_group_3_end_char.text()
        settings["format_group_3_sep_char"] = self.ui.format_group_3_sep_char.text()

        # Settings for word group 4
        settings["format_group_4_start_char"] = self.ui.format_group_4_start_char.text()
        settings["format_group_4_end_char"] = self.ui.format_group_4_end_char.text()
        settings["format_group_4_sep_char"] = self.ui.format_group_4_sep_char.text()

    def update_examples(self):
        settings = {}
        self._set_settings(settings)
        word_dict = self.processor.get_word_dict(settings)

        instruments_credits = {
            "guitar": ["Johnny Flux", "John Watson"],
            "guest guitar": ["Jimmy Page"],
            "additional guest solo guitar": ["Jimmy Page"],
        }
        instruments_example = self.build_example(instruments_credits, word_dict, settings)
        self.ui.example_instruments.setText(instruments_example)

        vocals_credits = {
            "additional solo lead vocals": ["Robert Plant"],
            "additional solo guest lead vocals": ["Sandy Denny"],
        }
        vocals_example = self.build_example(vocals_credits, word_dict, settings)
        self.ui.example_vocals.setText(vocals_example)

    def build_example(self, credits, word_dict, settings):
        prefix = "performer:"
        metadata = Metadata()
        for key, values in credits.items():
            self.processor.rewrite_tag(prefix + key, values, metadata, word_dict, settings)

        examples = []
        for key, values in metadata.rawitems():
            credit = "%s: %s" % (key, ", ".join(values))
            if credit.startswith(prefix):
                credit = credit[len(prefix):]
            examples.append(credit)
        return "\n".join(examples)


def enable(api: PluginApi):
    """Called when plugin is enabled."""

    # Register plugin options with their default values.
    api.plugin_config.register_option("format_group_additional", 3)
    api.plugin_config.register_option("format_group_guest", 4)
    api.plugin_config.register_option("format_group_solo", 3)
    api.plugin_config.register_option("format_group_vocals", 2)
    api.plugin_config.register_option("format_group_1_start_char", '')
    api.plugin_config.register_option("format_group_1_end_char", ' ')
    api.plugin_config.register_option("format_group_1_sep_char", '')
    api.plugin_config.register_option("format_group_2_start_char", ', ')
    api.plugin_config.register_option("format_group_2_end_char", '')
    api.plugin_config.register_option("format_group_2_sep_char", '')
    api.plugin_config.register_option("format_group_3_start_char", ' (')
    api.plugin_config.register_option("format_group_3_end_char", ')')
    api.plugin_config.register_option("format_group_3_sep_char", '')
    api.plugin_config.register_option("format_group_4_start_char", ' (')
    api.plugin_config.register_option("format_group_4_end_char", ')')
    api.plugin_config.register_option("format_group_4_sep_char", '')

    plugin = FormatPerformerTags(api)

    api.register_track_metadata_processor(plugin.format_performer_tags)
    api.register_options_page(FormatPerformerTagsOptionsPage)
