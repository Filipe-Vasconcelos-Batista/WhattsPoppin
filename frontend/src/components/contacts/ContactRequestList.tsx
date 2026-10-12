import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { ContactSummary } from '../../api/contacts';
import { initialsFor } from '../../messaging/conversationSummaries';
import { colorForId, colors } from '../../theme/colors';
import { Avatar } from '../Avatar';

type ContactRequestListProps = {
  requests: ContactSummary[];
  onAccept: (userId: string) => void;
  onRemove: (userId: string) => void;
};

export function ContactRequestList({ requests, onAccept, onRemove }: ContactRequestListProps) {
  if (requests.length === 0) return null;

  return (
    <View style={styles.section}>
      <Text style={styles.heading}>Pedidos</Text>
      {requests.map((request) => (
        <View key={request.user_id} style={styles.row}>
          <Avatar
            initials={initialsFor(request.display_name)}
            color={colorForId(request.user_id)}
            size={40}
          />
          <View style={styles.text}>
            <Text style={styles.name} numberOfLines={1}>
              {request.display_name}
            </Text>
            <Text style={styles.identifier} numberOfLines={1}>
              {request.identifier}
            </Text>
          </View>
          {request.status === 'pending_incoming' ? (
            <>
              <Pressable onPress={() => onAccept(request.user_id)} style={styles.accept}>
                <Text style={styles.acceptLabel}>Aceitar</Text>
              </Pressable>
              <Pressable onPress={() => onRemove(request.user_id)} style={styles.decline}>
                <Text style={styles.declineLabel}>Recusar</Text>
              </Pressable>
            </>
          ) : (
            <Pressable onPress={() => onRemove(request.user_id)} style={styles.decline}>
              <Text style={styles.declineLabel}>Cancelar</Text>
            </Pressable>
          )}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: 10,
    marginBottom: 16,
  },
  heading: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  text: {
    flex: 1,
  },
  name: {
    color: colors.textPrimary,
    fontSize: 15,
    fontWeight: '600',
  },
  identifier: {
    color: colors.textMuted,
    fontSize: 12,
  },
  accept: {
    backgroundColor: colors.accentCyan,
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  acceptLabel: {
    color: colors.background,
    fontSize: 13,
    fontWeight: '700',
  },
  decline: {
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  declineLabel: {
    color: colors.textSecondary,
    fontSize: 13,
  },
});
