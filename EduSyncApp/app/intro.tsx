import { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { Video, ResizeMode, AVPlaybackStatus } from 'expo-av';

type IntroScreenProps = {
  onDone: () => void;
};

export default function IntroScreen({ onDone }: IntroScreenProps) {
  const [finished, setFinished] = useState(false);

  const onPlaybackStatusUpdate = useCallback((status: AVPlaybackStatus) => {
    if (status.isLoaded && status.didJustFinish) {
      setFinished(true);
    }
  }, []);

  return (
    <View style={styles.container}>
      <Video
        source={require('@/assets/intro-video.mp4')}
        style={styles.video}
        resizeMode={ResizeMode.CONTAIN}
        shouldPlay
        isLooping={false}
        onPlaybackStatusUpdate={onPlaybackStatusUpdate}
      />
      <View style={styles.buttonWrap}>
        <TouchableOpacity style={styles.button} onPress={onDone} activeOpacity={0.85}>
          <Text style={styles.buttonText}>{finished ? 'Get Started' : 'Skip'}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  video: {
    flex: 1,
    width: '100%',
  },
  buttonWrap: {
    position: 'absolute',
    bottom: 60,
    width: '100%',
    maxWidth: 280,
    alignSelf: 'center',
  },
  button: {
    backgroundColor: '#00BCD4',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 14,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
});
