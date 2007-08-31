import kaa
import kaa.beacon

kaa.beacon.connect()

phone_keymap = ( '', 'abc', 'def', 'ghi', 'jkl', 'mno', 'pqrs', 'tuv', 'wxyz' )

# search for stuff starting with 'the' (843)
keys = '843'
regexp = ''
for k in keys:
    regexp += '[' + phone_keymap[int(k)-1] + phone_keymap[int(k)-1].upper() + ']'
regexp = kaa.beacon.QExpr('regexp', u'^%s.*' % regexp)

for m in kaa.beacon.query(type='audio', title=regexp).get():
    print m