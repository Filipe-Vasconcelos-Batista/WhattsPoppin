import { StyleSheet, Text, View } from 'react-native';

import { Avatar } from '../Avatar';
import { IconCircleButton } from '../IconCircleButton';
import { colorForId, colors } from '../../theme/colors';
import type { Contact } from '../../types/chat';

type ChatHeaderProps = {
  contact: Contact;
  onBackPress?: () => void;
};

/** Nome + identificador seguem a prioridade alcunha > nome de exibição >
 * identificador, e o identificador só aparece quando há ambiguidade
 * (ver identidade_e_nomes no projeto-chat-selfhosted.yaml). */
export function ChatHeader({ contact, onBackPress }: ChatHeaderProps) {
  const title = contact.nickname ?? contact.displayName;

  return (
    <View style={styles.row}>
      <IconCircleButton name="chevron-back" onPress={onBackPress} />
      <Avatar initials={initialsFor(contact)} color={colorForId(contact.id)} size={40} />

      <View style={styles.texts}>
        <Text style={styles.title} numberOfLines={1}>
          {title}
        </Text>
        {contact.isAmbiguous ? (
          <Text style={styles.subtitle} numberOfLines={1}>
            {contact.identifier} · tens outro &quot;{title}&quot;
          </Text>
        ) : null}
      </View>
    </View>
  );
}

function initialsFor(contact: Contact): string {
  return contact.displayName
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  texts: {
    flex: 1,
  },
  title: {
    color: colors.textPrimary,
    fontSize: 17,
    fontWeight: '700',
    textDecorationLine: 'underline',
  },
  subtitle: {
    color: '#F97316',
    fontSize: 12,
  },
});
